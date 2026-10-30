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
import random
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
# Writing a block is retried with an exponential backoff and full jitter,
# these are the base and the upper limit of the wait in seconds
RETRY_BACKOFF_BASE = 2
RETRY_BACKOFF_MAX = 60
# Timeout in seconds to establish the connection to the EBS direct API
CONNECT_TIMEOUT = 30
# Errors that cannot be fixed by sending the same request again. All other
# errors are retried, in particular a plain HTTP 400 without an error name
# that is seen on slow or unreliable network paths.
NON_RETRYABLE_ERROR_CODES = (
    'AccessDeniedException',
    'ResourceNotFoundException',
    'ServiceQuotaExceededException',
    'ValidationException'
)


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

    By default the image is written to a new EBS snapshot with the EBS direct
    APIs, no EC2 instance is needed for the upload. The root swap method
    additionally uses a donor instance (called helper instance in the code),
    it provides the meta data of the new image and gets a root volume that is
    created from the uploaded image. The donor instance is not accessed."""

    def __init__(self,
                 access_key=None,
                 backing_store='ssd',
                 billing_codes=None,
                 bootkernel=None,
                 config=None,
                 ena_support=False,
                 image_arch='x86_64',
                 image_description='AWS EC2 AMI',
                 image_name='default',
                 image_virt_type='hvm',
                 inst_user_name=None,
                 launch_ami=None,
                 launch_inst_type='m1.small',
                 region=None,
                 root_volume_size=10,
                 running_id=None,
                 secret_key=None,
                 security_group_ids='',
                 session_token=None,
                 sriov_type=None,
                 ssh_key_pair_name=None,
                 ssh_key_private_key_file=None,
                 ssh_timeout=300,
                 channel_timeout=900,
                 use_grub2=False,
                 use_private_ip=False,
                 vpc_subnet_id='',
                 use_enclave=False,
                 wait_count=1,
                 log_level=logging.INFO,
                 log_callback=None,
                 boot_mode=None,
                 tpm_support=None,
                 imds_support=None,
                 image_tags=None,
                 upload_workers=8,
                 upload_retries=8,
                 upload_timeout=300
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
        self.image_virt_type = 'hvm'
        self.imds_support = imds_support
        self.launch_ami_id = launch_ami
        self.launch_ins_type = launch_inst_type
        self.region = region
        self.root_volume_size = int(root_volume_size)
        self.running_id = running_id
        self.secret_key = secret_key
        self.session_token = session_token
        self.sriov_type = sriov_type
        self.tpm = tpm_support
        self.vpc_subnet_id = vpc_subnet_id
        self.use_enclave = use_enclave
        self.wait_count = wait_count

        self.created_volumes = []
        self.default_sleep = 10
        # Instances that are terminated by the clean up. An instance given
        # with running_id is only added when the swap of its root volume
        # starts, a failure before that must leave it untouched.
        self.instance_ids = []
        self.operation_complete = False
        self.temporary_snapshot_ids = []
        self.helper_instance = None
        self.aborted = False
        self.image_tags = image_tags
        self.pending_snapshot_id = None
        try:
            self.upload_workers = int(upload_workers)
        except (TypeError, ValueError):
            self.upload_workers = 0

        if image_virt_type != 'hvm':
            raise EC2UploadImgException(
                'Only hvm images are supported, the virtualization type '
                '"%s" is no longer supported' % image_virt_type
            )
        if bootkernel or use_grub2:
            self.log.warning(
                'The bootkernel and use_grub2 arguments are deprecated and '
                'ignored, para-virtual images are no longer supported'
            )
        self._warn_deprecated_arguments(
            inst_user_name=inst_user_name,
            security_group_ids=security_group_ids,
            ssh_key_pair_name=ssh_key_pair_name,
            ssh_key_private_key_file=ssh_key_private_key_file,
            ssh_timeout=ssh_timeout != 300,
            channel_timeout=channel_timeout != 900,
            use_private_ip=use_private_ip
        )
        if self.upload_workers < 1:
            raise EC2UploadImgException(
                'upload_workers must be an integer greater than 0'
            )
        self.upload_retries = self._positive_int(
            upload_retries, 'upload_retries'
        )
        self.upload_timeout = self._positive_int(
            upload_timeout, 'upload_timeout'
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

    def _warn_deprecated_arguments(self, **arguments):
        """Warn about the arguments that were only used for the upload with
           ssh, the image is uploaded with the EBS direct APIs"""
        ignored = sorted(name for name, value in arguments.items() if value)
        if ignored:
            self.log.warning(
                'The following arguments are deprecated and ignored, the '
                'image is uploaded with the EBS direct APIs and no ssh '
                'connection is needed: %s' % ', '.join(ignored)
            )

    # ---------------------------------------------------------------------
    @staticmethod
    def _positive_int(value, name):
        """Return the value as integer, it must be greater than 0"""
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = 0
        if number < 1:
            raise EC2UploadImgException(
                '%s must be an integer greater than 0' % name
            )

        return number

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
    def _attach_volume(self, volume, device):
        """Attach the given volume to the donor instance"""
        if self.aborted:
            return
        self._connect().attach_volume(
                VolumeId=volume['VolumeId'],
                InstanceId=self.helper_instance['InstanceId'],
                Device=device)
        self.log.debug('Wait for volume attachment')
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('volume_in_use')
        repeat_count = 1
        error_msg = 'Unable to attach volume'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    VolumeIds=[volume['VolumeId']],
                    Filters=[
                        {
                            'Name': 'attachment.status',
                            'Values': ['attached']
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
    def _check_image_exists(self):
        """Check if an image with the given name already exists"""
        my_images = self._get_owned_images()
        for image in my_images:
            if image['Name'] == self.image_name:
                msg = 'Image with name "%s" already exists' % self.image_name
                raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _check_subnet_exists(self):
        """Verify that the subnet being used for the helper instance
           exists"""
        try:
            self._connect().describe_subnets(SubnetIds=[self.vpc_subnet_id])
        except Exception:
            error_msg = 'Specified subnet %s not found' % self.vpc_subnet_id
            raise EC2UploadImgException(error_msg)

    # ---------------------------------------------------------------------
    def _check_virt_type_consistent(self):
        """When using root swap the virtualization type of the helper
           image and the target image must be the same"""
        if self.launch_ami_id:
            image = self._connect().describe_images(
                ImageIds=[self.launch_ami_id]
            )['Images'][0]
        elif self.running_id:
            helper_instance = self._get_helper_instance()
            image = self._connect().describe_images(
                ImageIds=[helper_instance['ImageId']]
            )['Images'][0]
        else:
            error_msg = 'Could not determine helper image virtualization '
            error_msg += 'type necessary for root swap method'
            raise EC2UploadImgException(error_msg)

        if not self.image_virt_type == image['VirtualizationType']:
            error_msg = 'Virtualization type of the helper image and the '
            error_msg += 'target image must be the same when using '
            error_msg += 'root-swap method for image creation.'
            raise EC2UploadImgException(error_msg)

    # ---------------------------------------------------------------------
    def _check_wait_status(
            self,
            wait_status,
            error_msg,
            repeat_count,
            skip_cleanup=False
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
                if not skip_cleanup:
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
        if self.instance_ids:
            self._connect().terminate_instances(InstanceIds=self.instance_ids)
            waiter = self._connect().get_waiter('instance_terminated')
            if self.helper_instance:
                instance_ids = [self.helper_instance['InstanceId']]
            else:
                instance_ids = list(self.instance_ids)
            repeat_count = 1
            error_msg = 'Instance did not stop within allotted time'
            while repeat_count <= self.wait_count:
                try:
                    wait_status = waiter.wait(
                        InstanceIds=instance_ids,
                        Filters=[
                            {
                                'Name': 'instance-state-name',
                                'Values': ['terminated']
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
                    repeat_count,
                    skip_cleanup=True
                )
        if self.created_volumes:
            for volume in self.created_volumes:
                self._detach_volume(volume)
                self._remove_volume(volume)

        self.created_volumes = []
        self.instance_ids = []
        self._delete_temporary_snapshots()

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
    def _create_image_root_volume(self, source):
        """Create a volume with the content of the image in the availability
           zone of the donor instance. The donor instance provides the meta
           data for the new image. The image is written to a temporary
           snapshot with the EBS direct APIs, the volume is created from it"""
        if self.aborted:
            return
        if self.vpc_subnet_id:
            self._check_subnet_exists()
        if self.running_id:
            # When using an already running instance, simply look up this one
            self.helper_instance = self._get_helper_instance()
        snapshot = self._create_snapshot_from_image(source, temporary=True)
        if not snapshot or self.aborted:
            self._clean_up()
            return
        if not self.running_id:
            self.helper_instance = self._launch_helper_instance()
        if not self.helper_instance or self.aborted:
            self._clean_up()
            return
        target_root_volume = self._create_volume(
            self.root_volume_size, snapshot['SnapshotId']
        )
        if not target_root_volume or self.aborted:
            self._clean_up()
            return

        return target_root_volume

    # ---------------------------------------------------------------------
    def _create_volume(self, size, snapshot_id=None):
        """Create a volume, optionally from a snapshot"""
        if self.aborted:
            return
        volume_args = {
            'Size': int(size),
            'AvailabilityZone': self.zone,
            'VolumeType': 'gp2'
        }
        if snapshot_id:
            volume_args['SnapshotId'] = snapshot_id
        volume = self._connect().create_volume(**volume_args)
        self.log.debug(
            'Waiting for volume creation: {}'.format(volume['VolumeId'])
        )
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('volume_available')
        repeat_count = 1
        error_msg = 'Time out for Volume creation reached, '
        error_msg += 'terminating instance and deleting volume'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    VolumeIds=[volume['VolumeId']],
                    Filters=[
                        {
                            'Name': 'status',
                            'Values': ['available']
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

        self.created_volumes.append(volume)

        return volume

    # ---------------------------------------------------------------------
    def _detach_volume(self, volume):
        """Detach the given volume"""
        if not volume:
            return
        volume = self._connect().describe_volumes(
            VolumeIds=[volume['VolumeId']])['Volumes'][0]
        if volume['State'] == 'available':
            # Not attached, nothing to do
            return 1

        self._connect().detach_volume(VolumeId=volume['VolumeId'])
        self.log.debug('Wait for volume to detach')
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('volume_available')
        repeat_count = 1
        error_msg = 'Unable to detach volume'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    VolumeIds=[volume['VolumeId']],
                    Filters=[
                        {
                            'Name': 'status',
                            'Values': ['available']
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

        return 1

    # ---------------------------------------------------------------------
    def _determine_root_device(self):
        """Figure out what the root device should be"""
        return '/dev/sda1'

    # ---------------------------------------------------------------------
    def _get_helper_instance(self):
        """Returns handle to running instance"""
        helper_instance = self._connect().describe_instances(
            InstanceIds=[self.running_id])['Reservations'][0]['Instances'][0]
        if helper_instance['State']['Name'] != 'running':
            msg = 'Helper instance %s is not running' % self.running_id
            raise EC2UploadImgException(msg)

        self.vpc_subnet_id = helper_instance['SubnetId']
        self._set_zone_to_use()

        return helper_instance

    # ---------------------------------------------------------------------
    def _launch_helper_instance(self):
        """Launch the donor instance that provides the meta data for the new
           image, it is not accessed, it is stopped and gets the new root
           volume"""
        if self.aborted:
            return
        self._set_zone_to_use()
        launch_args = {
            'ImageId': self.launch_ami_id,
            'MinCount': 1,
            'MaxCount': 1,
            'InstanceType': self.launch_ins_type,
            'Placement': {'AvailabilityZone': self.zone},
            'EnclaveOptions': {'Enabled': self.use_enclave},
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'ec2uploadimg-helper-instance'
                        }
                    ]
                }
            ]
        }
        if self.vpc_subnet_id:
            launch_args['SubnetId'] = self.vpc_subnet_id
        instance = self._connect().run_instances(**launch_args)['Instances'][0]

        self.instance_ids.append(instance['InstanceId'])

        self.log.debug(
            'Waiting for instance: {}'.format(instance['InstanceId'])
        )
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('instance_running')
        repeat_count = 1
        error_msg = 'Time out for instance creation reached, '
        error_msg += 'terminating instance'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    InstanceIds=[instance['InstanceId']],
                    Filters=[
                        {
                            'Name': 'instance-state-name',
                            'Values': ['running']
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

        return instance

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
    def _remove_volume(self, volume):
        """Delete the given volume from EC2"""
        if not volume:
            return
        self._connect().delete_volume(VolumeId=volume['VolumeId'])

        return 1

    # ---------------------------------------------------------------------
    def _set_zone_to_use(self):
        """Set the availability zone to use for all operations"""
        if self.vpc_subnet_id:
            # If a subnet is given we need to launch the helper instance
            # in the AZ wher ethe subnet is defined
            subnet = self._connect().describe_subnets(
                SubnetIds=[self.vpc_subnet_id]
            )['Subnets'][0]
            self.zone = subnet['AvailabilityZone']
            return
        zones = self._connect().describe_availability_zones()[
            'AvailabilityZones']
        availability_zones = []
        for zone in zones:
            availability_zones.append(zone['ZoneName'])
        self.zone = availability_zones[-1]

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
                connect_timeout=CONNECT_TIMEOUT,
                read_timeout=self.upload_timeout,
                # Failed blocks are retried by _put_snapshot_block, keep the
                # retries of botocore short to not multiply the attempts
                retries={'max_attempts': 2, 'mode': 'standard'}
            )
        )

    # ---------------------------------------------------------------------
    def _create_snapshot_from_image(self, source, temporary=False):
        """Write the raw image data of the source file to a new snapshot.
           A temporary snapshot is deleted when the resources are cleaned up,
           it is the source of a volume and not the result of the upload"""
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

        if temporary:
            self.temporary_snapshot_ids.append(snapshot_id)
        self._wait_for_snapshot(snapshot_id)

        return {'SnapshotId': snapshot_id}

    # ---------------------------------------------------------------------
    def _claim_running_instance(self):
        """The root volume of the donor instance is about to be replaced.
           From here on an instance that was given with running_id is cleaned
           up with the resources created by the upload"""
        if self.running_id and self.running_id not in self.instance_ids:
            self.instance_ids.append(self.running_id)

    # ---------------------------------------------------------------------
    def _delete_temporary_snapshots(self):
        """Delete the snapshots that were only needed to create volumes"""
        snapshot_ids = self.temporary_snapshot_ids
        self.temporary_snapshot_ids = []
        for snapshot_id in snapshot_ids:
            self.log.debug(
                'Deleting temporary snapshot: {}'.format(snapshot_id)
            )
            try:
                self._connect().delete_snapshot(SnapshotId=snapshot_id)
            except Exception as e:
                self.log.warning(
                    'Unable to delete temporary snapshot %s: %s' % (
                        snapshot_id, e
                    )
                )

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
            filename.find('.tgz') != -1
        ):
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
    def _is_retryable_error(self, error):
        """Tell if writing the block again may succeed"""
        if isinstance(error, botocore.exceptions.ClientError):
            code = error.response.get('Error', {}).get('Code')
            return code not in NON_RETRYABLE_ERROR_CODES
        return isinstance(
            error,
            (
                botocore.exceptions.BotoCoreError,
                ConnectionError,
                TimeoutError
            )
        )

    # ---------------------------------------------------------------------
    def _log_block_failure(self, index, attempt, error):
        """Log the details of a failed attempt to write a block"""
        details = '%s: %s' % (type(error).__name__, error)
        if isinstance(error, botocore.exceptions.ClientError):
            meta = error.response.get('ResponseMetadata', {})
            details = 'HTTP status %s, request id %s, %s' % (
                meta.get('HTTPStatusCode'),
                meta.get('RequestId'),
                details
            )
        self.log.warning(
            'Writing block %d failed, attempt %d of %d: %s' % (
                index, attempt, self.upload_retries, details
            )
        )

    # ---------------------------------------------------------------------
    def _wait_before_retry(self, attempt):
        """Wait with an exponential backoff and full jitter, the wait ends
           early if the upload gets aborted"""
        limit = min(RETRY_BACKOFF_MAX, RETRY_BACKOFF_BASE * 2 ** attempt)
        remaining = random.uniform(0, limit)
        while remaining > 0 and not self.aborted:
            step = min(remaining, 1)
            time.sleep(step)
            remaining -= step

    # ---------------------------------------------------------------------
    def _put_snapshot_block(self, ebs, snapshot_id, index, data):
        """Write a block to the snapshot, return block index and checksum.
           Writing is retried as the data of a block can be written again."""
        digest = hashlib.sha256(data).digest()
        for attempt in range(1, self.upload_retries + 1):
            try:
                ebs.put_snapshot_block(
                    SnapshotId=snapshot_id,
                    BlockIndex=index,
                    BlockData=data,
                    DataLength=len(data),
                    Checksum=base64.b64encode(digest).decode('ascii'),
                    ChecksumAlgorithm='SHA256'
                )
                return index, digest
            except Exception as error:
                self._log_block_failure(index, attempt, error)
                if (
                    not self._is_retryable_error(error) or
                    attempt == self.upload_retries or
                    self.aborted
                ):
                    if not self._is_retryable_error(error):
                        raise
                    msg = 'Unable to write block %d to snapshot %s after '
                    msg += '%d attempt(s), last error: %s'
                    raise EC2UploadImgException(
                        msg % (index, snapshot_id, attempt, error)
                    )
                self._wait_before_retry(attempt)

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
            max_workers=self.upload_workers
        ) as pool:
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
                            bytes_read >= next_progress
                        ):
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

    def create_image_use_root_swap(self, source):
        """Creae an AMI (Amazon Machine Image) from the given source using
           the root swap method"""

        self._check_virt_type_consistent()
        try:
            target_root_volume = self._create_image_root_volume(source)
        except Exception:
            # Remove what was created, an instance given with running_id is
            # not touched before the swap of the root volume
            try:
                self._clean_up()
            except Exception as error:
                self.log.warning('Clean up failed: %s' % error)
            raise
        if not target_root_volume:
            # The upload was aborted
            return
        self._claim_running_instance()
        self._connect().stop_instances(InstanceIds=self.instance_ids)
        self.log.debug('Waiting for helper instance to stop')
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('instance_stopped')
        repeat_count = 1
        error_msg = 'Instance did not stop within allotted time'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    InstanceIds=[self.helper_instance['InstanceId']],
                    Filters=[
                        {
                            'Name': 'instance-state-name',
                            'Values': ['stopped']
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

        # Find the current root volume
        my_volumes = self._connect().describe_volumes()['Volumes']
        current_root_volume = None
        device_id = None
        for volume in my_volumes:
            attached = volume['Attachments']
            if not attached:
                continue
            attached_to_instance = attached[0].get('InstanceId')
            if attached_to_instance == self.helper_instance['InstanceId']:
                current_root_volume = volume
                device_id = attached[0].get('Device')
                break

        self._detach_volume(current_root_volume)
        self._attach_volume(target_root_volume, device_id)
        self.log.debug('Creating new image')
        instance_info = self._connect().describe_instances(
            InstanceIds=[self.helper_instance['InstanceId']]
        )
        helper_instance = instance_info['Reservations'][0]['Instances']
        helper_dev_map = helper_instance[0]['BlockDeviceMappings'][0]
        if self.backing_store == 'mag':
            backing_store = 'standard'
        else:
            backing_store = 'gp2'
        block_device_map = {
            'DeviceName': helper_dev_map['DeviceName'],
            'Ebs': {
                'DeleteOnTermination':
                helper_dev_map['Ebs']['DeleteOnTermination'],
                'VolumeSize': self.root_volume_size,
                'VolumeType': backing_store
            }
        }
        ami = self._connect().create_image(
            BlockDeviceMappings=[block_device_map],
            InstanceId=self.helper_instance['InstanceId'],
            Name=self.image_name,
            Description=self.image_description,
            NoReboot=True
        )

        self.log.debug('Waiting for new image creation')
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('image_available')
        repeat_count = 1
        error_msg = 'Image creation did not complete within '
        error_msg += 'allotted time skipping clean up'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    ImageIds=[ami['ImageId']],
                    Filters=[
                        {
                            'Name': 'state',
                            'Values': ['available']
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
                repeat_count,
                True
            )

        self._clean_up()

        self._tag_image(ami['ImageId'])
        return ami['ImageId']

    # ---------------------------------------------------------------------
    def create_snapshot(self, source):
        """Create a snapshot from the given source"""
        if self.log_level == logging.DEBUG:
            print()
        snapshot = self._create_snapshot_from_image(source)
        self._clean_up()
        return snapshot
