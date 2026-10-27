# Copyright 2021 SUSE LLC
#
# This file is part of ec2imgutils
#
# eec2imgutils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2imgutils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2uploadimg. If not, see <http://www.gnu.org/licenses/>.

import base64
import botocore
import botocore.config
import concurrent.futures
import contextlib
import hashlib
import logging
import lzma
import os
import sys
import tarfile
import threading
import time
import uuid


from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2UploadImgException


# Time in minutes after which AWS cancels a snapshot started with the EBS
# direct APIs if it is not completed, valid range is 10 to 4320
SNAPSHOT_TIMEOUT_MINUTES = 1440
# Amount of raw image data between two progress indicator dots (debug mode)
PROGRESS_STEP_BYTES = 128 * 1024 * 1024


def _read_exactly(stream, size):
    """Read size bytes from the stream, a shorter result means the end of the
       stream was reached"""
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)

    return b''.join(chunks)


class EC2ImageUploader(EC2ImgUtils):
    """Upload the given image to Amazon EC2

    The image is written to a new EBS snapshot with the EBS direct APIs, no
    EC2 instance is involved."""

    def __init__(self,
                 access_key=None,
                 backing_store='ssd',
                 billing_codes=None,
                 config=None,
                 ena_support=False,
                 image_arch='x86_64',
                 image_description='AWS EC2 AMI',
                 image_name='default',
                 region=None,
                 root_volume_size=10,
                 secret_key=None,
                 session_token=None,
                 sriov_type=None,
                 wait_count=1,
                 log_level=logging.INFO,
                 log_callback=None,
                 boot_mode=None,
                 tpm_support=None,
                 imds_support=None,
                 image_tags=None,
                 upload_workers=8
                 ):
        EC2ImgUtils.__init__(
            self,
            log_level=log_level,
            log_callback=log_callback
        )

        self.access_key = access_key
        self.backing_store = backing_store
        self.billing_codes = billing_codes
        self.boot_mode = boot_mode
        self.ena_support = ena_support
        self.image_arch = image_arch
        self.image_description = image_description
        self.image_name = image_name
        self.imds_support = imds_support
        self.region = region
        self.root_volume_size = int(root_volume_size)
        self.secret_key = secret_key
        self.session_token = session_token
        self.sriov_type = sriov_type
        self.tpm = tpm_support
        self.wait_count = wait_count

        self.default_sleep = 10
        self.operation_complete = False
        self.aborted = False
        self.image_tags = image_tags
        self.pending_snapshot_id = None
        try:
            self.upload_workers = int(upload_workers)
        except (TypeError, ValueError):
            self.upload_workers = 0

        if self.upload_workers < 1:
            raise EC2UploadImgException(
                'upload_workers must be an integer greater than 0'
            )
        if sriov_type and sriov_type != 'simple':
            raise EC2UploadImgException(
                'sriov_type can only be None or simple'
            )
        tpm_versions = ['2.0', 'v2.0']
        if tpm_support and tpm_support not in tpm_versions:
            raise EC2UploadImgException(
                'tpm_support must be one of %s' % str(tpm_versions)
            )
        imds_versions = ['2.0', 'v2.0']
        if imds_support and imds_support not in imds_versions:
            raise EC2UploadImgException(
                'imds_support must be one of %s' % str(imds_versions)
            )

    def abort(self):
        """
        Set the abort flag to take appropriate action and stop image creation.
        """
        self.log.debug(
            "Aborted upload, please wait while AWS resources get cleaned"
            " up. This may take a few minutes!"
        )
        self.aborted = True

    # ---------------------------------------------------------------------
    def _check_image_exists(self):
        """Check if an image with the given name already exists"""
        my_images = self._get_owned_images()
        for image in my_images:
            if image['Name'] == self.image_name:
                msg = 'Image with name "%s" already exists' % self.image_name
                raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _check_wait_status(
            self,
            wait_status,
            error_msg,
            repeat_count
    ):
        """Check the wait status form the waiter and take appropriate action"""
        if wait_status:
            if self.log_level == logging.DEBUG:
                print()
            if repeat_count == self.wait_count:
                self.operation_complete = True
                if self.log_level == logging.DEBUG:
                    self.progress_timer.cancel()
                time.sleep(self.default_sleep)  # Wait for the thread
                self._clean_up()
                raise EC2UploadImgException(error_msg)
            repeat_count += 1
            self.log.info('Entering wait loop number %d of %d' % (
                repeat_count,
                self.wait_count
            ))
            self.operation_complete = False
            self._show_progress()
        else:
            repeat_count = self.wait_count + 1
            self.operation_complete = True
            if self.log_level == logging.DEBUG:
                self.progress_timer.cancel()
            time.sleep(self.default_sleep)  # Wait for the thread
            if self.log_level == logging.DEBUG:
                print()

        return repeat_count

    # ---------------------------------------------------------------------
    def _clean_up(self):
        """Clean up the given resources"""
        self._delete_pending_snapshot()

    # ---------------------------------------------------------------------
    def _create_block_device_map(self, snapshot):
        """Create a block device map with the given snapshot"""
        if self.aborted:
            return
        # We assume the root image has 1 partition (either case)
        root_device_name = self._determine_root_device()

        if self.backing_store == 'mag':
            backing_store = 'standard'
        elif self.backing_store == 'ssd':
            backing_store = 'gp3'
        else:
            backing_store = self.backing_store

        block_device_map = {
            'DeviceName': root_device_name,
            'Ebs': {
                'SnapshotId': snapshot['SnapshotId'],
                'VolumeSize': self.root_volume_size,
                'DeleteOnTermination': True,
                'VolumeType': backing_store
            }
        }

        return [block_device_map]

    # ---------------------------------------------------------------------
    def _determine_root_device(self):
        """Figure out what the root device should be"""
        return '/dev/sda1'

    # ---------------------------------------------------------------------
    def _register_image(self, snapshot):
        """Register an image from the given snapshot"""
        if self.aborted:
            return
        block_device_map = self._create_block_device_map(snapshot)
        self.log.debug('Registering image')

        root_device_name = self._determine_root_device()
        register_args = {
            'Architecture': self.image_arch,
            'BlockDeviceMappings': block_device_map,
            'Description': self.image_description.strip(),
            'EnaSupport': self.ena_support,
            'Name': self.image_name,
            'RootDeviceName': root_device_name,
            'VirtualizationType': 'hvm'
        }
        if self.billing_codes:
            register_args['BillingProducts'] = self.billing_codes.split(',')
        if self.boot_mode:
            register_args['BootMode'] = self.boot_mode
        if self.sriov_type:
            register_args['SriovNetSupport'] = self.sriov_type
        if self.tpm:
            tpm_version = self.tpm
            if not tpm_version.startswith('v'):
                tpm_version = 'v%s' % tpm_version
            register_args['TpmSupport'] = tpm_version
        if self.imds_support:
            imds_version = self.imds_support
            if not imds_version.startswith('v'):
                imds_version = 'v%s' % imds_version
            register_args['ImdsSupport'] = imds_version

        ami = self._connect().register_image(**register_args)

        return ami['ImageId']

    # ---------------------------------------------------------------------
    def _show_progress(self, timeout_counter=1):
        """Progress indicator"""

        # Give EC2 some time to update it's state
        # Whenever _show_progress is called we get a waiter from EC2
        # The wait operation may fail if the EC2 state is not yet updated.
        # Taking a nap on the client side avoids the problem
        time.sleep(self.default_sleep)

        if self.log_level == logging.DEBUG:
            print('. ', end=' ')
            sys.stdout.flush()
            timeout_counter += 1
            if not self.operation_complete:
                self.progress_timer = threading.Timer(
                    self.default_sleep,
                    self._show_progress,
                    args=[timeout_counter]
                )
                self.progress_timer.start()

    # ---------------------------------------------------------------------
    def _tag_image(self, ami_id):
        """Tag the image"""

        if self.image_tags:
            self.log.debug('Applying tags')
            try:
                self._connect().create_tags(
                    Resources=[ami_id], Tags=self.image_tags
                )
            except botocore.exceptions.ParamValidationError:
                msg = 'Tag appllication failed, please apply tags '
                msg += 'manually via the aws tool or the web console. '
                msg += 'Tag value validation failed.'
                self.log.debug(msg)

    # ---------------------------------------------------------------------
    # Image upload using the EBS direct APIs
    # ---------------------------------------------------------------------
    def _complete_snapshot(self, ebs, snapshot_id, digests):
        """Seal the snapshot, the checksum is the SHA256 of the concatenated
           raw block checksums in ascending block index order"""
        aggregate = hashlib.sha256()
        for index in sorted(digests):
            aggregate.update(digests[index])
        self.log.debug('Completing snapshot: {}'.format(snapshot_id))
        ebs.complete_snapshot(
            SnapshotId=snapshot_id,
            ChangedBlocksCount=len(digests),
            Checksum=base64.b64encode(aggregate.digest()).decode('ascii'),
            ChecksumAlgorithm='SHA256',
            ChecksumAggregationMethod='LINEAR'
        )
        # From here on the snapshot is sealed by AWS, nothing to abort
        self.pending_snapshot_id = None

    # ---------------------------------------------------------------------
    def _connect_ebs(self):
        """Connect to the EBS direct API, one connection per upload worker"""
        return self._connect(
            service='ebs',
            config=botocore.config.Config(
                max_pool_connections=self.upload_workers,
                retries={'max_attempts': 10, 'mode': 'adaptive'}
            )
        )

    # ---------------------------------------------------------------------
    def _create_snapshot_from_image(self, source):
        """Write the raw image data of the source file to a new snapshot
           without involving an EC2 instance"""
        if self.aborted:
            return
        self._check_image_exists()
        try:
            ebs = self._connect_ebs()
            snapshot_id, block_size = self._start_snapshot(ebs)
            digests = self._upload_snapshot_blocks(
                ebs, snapshot_id, block_size, source
            )
            if self.aborted:
                self._clean_up()
                return
            self._complete_snapshot(ebs, snapshot_id, digests)
        except Exception:
            self._clean_up()
            raise

        self._wait_for_snapshot(snapshot_id)

        return {'SnapshotId': snapshot_id}

    # ---------------------------------------------------------------------
    def _delete_pending_snapshot(self):
        """Delete the snapshot that was started but never completed"""
        snapshot_id = self.pending_snapshot_id
        if not snapshot_id:
            return
        self.pending_snapshot_id = None
        self.log.debug('Deleting incomplete snapshot: {}'.format(snapshot_id))
        try:
            self._connect().delete_snapshot(SnapshotId=snapshot_id)
        except Exception as e:
            self.log.warning(
                'Unable to delete incomplete snapshot %s: %s' % (
                    snapshot_id, e
                )
            )

    # ---------------------------------------------------------------------
    @contextlib.contextmanager
    def _open_raw_image(self, source):
        """Provide a stream of the raw image data contained in the source
           file. The source is either a raw or xz compressed raw file or a
           tar archive, optionally compressed, containing one. Nothing is
           unpacked to disk"""
        filename = os.path.basename(source)
        if (
                filename.find('.tar') != -1 or
                filename.find('.tbz') != -1 or
                filename.find('.tgz') != -1):
            with tarfile.open(source, 'r|*') as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    name = member.name.strip()
                    if name[-2:] == 'xz':
                        self.log.debug('Inflating image: {}'.format(name))
                        with lzma.LZMAFile(archive.extractfile(member)) as raw:
                            yield raw
                        return
                    if name[-4:] == '.raw':
                        yield archive.extractfile(member)
                        return
        elif filename[-2:] == 'xz':
            self.log.debug('Inflating image: {}'.format(filename))
            with lzma.open(source, 'rb') as raw:
                yield raw
            return
        elif filename[-3:] == 'raw':
            with open(source, 'rb') as raw:
                yield raw
            return

        msg = 'Unable to find raw image file with .raw extension'
        raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _put_snapshot_block(self, ebs, snapshot_id, index, data):
        """Write a block to the snapshot, return block index and checksum"""
        digest = hashlib.sha256(data).digest()
        ebs.put_snapshot_block(
            SnapshotId=snapshot_id,
            BlockIndex=index,
            BlockData=data,
            DataLength=len(data),
            Checksum=base64.b64encode(digest).decode('ascii'),
            ChecksumAlgorithm='SHA256'
        )

        return index, digest

    # ---------------------------------------------------------------------
    def _start_snapshot(self, ebs):
        """Start a snapshot with the size of the root volume of the image"""
        snapshot = ebs.start_snapshot(
            VolumeSize=self.root_volume_size,
            Description=self.image_description,
            ClientToken=str(uuid.uuid4()),
            Timeout=SNAPSHOT_TIMEOUT_MINUTES
        )
        self.pending_snapshot_id = snapshot['SnapshotId']
        self.log.debug(
            'Started snapshot: {}'.format(snapshot['SnapshotId'])
        )

        return snapshot['SnapshotId'], snapshot.get('BlockSize', 524288)

    # ---------------------------------------------------------------------
    def _upload_snapshot_blocks(self, ebs, snapshot_id, block_size, source):
        """Upload the raw image data to the snapshot using multiple threads.
           Blocks containing only zeros are not written. Returns the
           checksums of the written blocks by block index."""
        max_blocks = (self.root_volume_size * 1024 ** 3) // block_size
        zero_block = bytes(block_size)
        max_pending = self.upload_workers * 2
        digests = {}
        pending = set()
        bytes_read = 0
        next_progress = PROGRESS_STEP_BYTES

        def collect(done):
            for future in done:
                index, digest = future.result()
                digests[index] = digest

        self.log.debug('Uploading image file: {}'.format(source))
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.upload_workers) as pool:
            try:
                with self._open_raw_image(source) as stream:
                    index = 0
                    while not self.aborted:
                        data = _read_exactly(stream, block_size)
                        if not data:
                            break
                        if index >= max_blocks:
                            msg = 'The raw image is larger than the root '
                            msg += 'volume size of %dG, use '
                            msg += '--root-volume-size to increase it'
                            raise EC2UploadImgException(
                                msg % self.root_volume_size
                            )
                        bytes_read += len(data)
                        if len(data) < block_size:
                            data = data.ljust(block_size, b'\0')
                        if data != zero_block:
                            pending.add(pool.submit(
                                self._put_snapshot_block,
                                ebs,
                                snapshot_id,
                                index,
                                data
                            ))
                            if len(pending) >= max_pending:
                                done, pending = concurrent.futures.wait(
                                    pending,
                                    return_when=(
                                        concurrent.futures.FIRST_COMPLETED
                                    )
                                )
                                collect(done)
                        index += 1
                        if (
                                self.log_level == logging.DEBUG and
                                bytes_read >= next_progress):
                            print('.', end=' ')
                            sys.stdout.flush()
                            next_progress += PROGRESS_STEP_BYTES
                done, pending = concurrent.futures.wait(pending)
                collect(done)
            except BaseException:
                for future in pending:
                    future.cancel()
                raise
        if self.log_level == logging.DEBUG:
            print()

        return digests

    # ---------------------------------------------------------------------
    def _wait_for_snapshot(self, snapshot_id):
        """Wait for the given snapshot to reach the completed state"""
        if self.aborted:
            return
        self.log.debug(
            'Waiting for snapshot creation: {}'.format(snapshot_id)
        )
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('snapshot_completed')
        repeat_count = 1
        error_msg = 'Unable to create snapshot'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    SnapshotIds=[snapshot_id],
                    Filters=[
                        {
                            'Name': 'status',
                            'Values': ['completed']
                        }
                    ]
                )
            except Exception:
                wait_status = 1
            if self.log_level == logging.DEBUG:
                self.progress_timer.cancel()
            repeat_count = self._check_wait_status(
                wait_status,
                error_msg,
                repeat_count
            )

    # ---------------------------------------------------------------------
    def create_image(self, source):
        """Create an AMI (Amazon Machine Image) from the given source"""
        snapshot = self.create_snapshot(source)
        if not snapshot:
            # Upload was aborted
            return

        ami = self._register_image(snapshot)
        self._tag_image(ami)

        return ami

    # ---------------------------------------------------------------------
    def create_image_from_snapshot(self, source):
        """Create an AMI (Amazon Machine Image) from the given snapshot"""

        try:
            response = self._connect().describe_snapshots(SnapshotIds=[source])

        except Exception:
            self.log.error('Unable to retrieve details for snapshot %s',
                           source)
            sys.exit(1)

        snapshot = response['Snapshots'][0]
        ami = self._register_image(snapshot)
        self._tag_image(ami)

        return ami

    # ---------------------------------------------------------------------
    def create_snapshot(self, source):
        """Create a snapshot from the given source"""
        if self.log_level == logging.DEBUG:
            print()
        snapshot = self._create_snapshot_from_image(source)
        self._clean_up()
        return snapshot
