# Copyright 2015 SUSE LLC, Robert Schweikert
#
# This file is part of ec2uploadimg.
#
# ec2uploadimg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2uploadimg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2uploadimg. If not, see <http://www.gnu.org/licenses/>.

import boto
import boto.ec2
import os
import paramiko
import sys
import time


from .ec2utils import EC2Utils
from .ec2UtilsExceptions import *


class EC2ImageUploader(EC2Utils):
    """Upload the given image to Amazon EC2"""

    def __init__(self,
                 access_key=None,
                 backing_store='ssd',
                 bootkernel=None,
                 config=None,
                 image_arch='x86_64',
                 image_description='AWS EC2 AMI',
                 image_name='default',
                 image_virt_type='para',
                 inst_user_name=None,
                 launch_ami=None,
                 launch_inst_type='m1.small',
                 operation_timeout=300,
                 root_volume_size=10,
                 secret_key=None,
                 sriov_type=None,
                 ssh_key_pair_name=None,
                 ssh_key_private_key_file=None,
                 use_grub2=False,
                 verbose=None):
        EC2Utils.__init__(self)

        self.access_key = access_key
        self.backing_store = backing_store
        self.bootkernel = bootkernel
        self.image_arch = image_arch
        self.image_description = image_description
        self.image_name = image_name
        self.image_virt_type = image_virt_type
        self.inst_user_name = inst_user_name
        self.launch_ami = launch_ami
        self.launch_ins_type = launch_inst_type
        self.operation_timeout = operation_timeout
        self.root_volume_size=int(root_volume_size)
        self.secret_key = secret_key
        self.sriov_type = sriov_type
        self.ssh_key_pair_name = ssh_key_pair_name
        self.ssh_key_private_key_file = ssh_key_private_key_file
        self.use_grub2 = use_grub2
        self.verbose = verbose

        self.created_volumes = []
        self.default_sleep = 10
        self.device_ids = ['f', 'g', 'h', 'i', 'j']
        self.instance_ids = []
        self.next_device_id = 0
        self.percent_transferred = 0
        self.region = None
        self.ssh_client = None
        self.storage_volume_size = 2 * self.root_volume_size

    # ---------------------------------------------------------------------
    def _attach_volume(self, instance, volume, device=None):
        """Attach the given volume to the given instance"""
        if not device:
            device = self._get_next_disk_id()
        volume.attach(instance_id=instance.id, device=device)
        if self.verbose:
            print 'Wait for volume attachment'
        wait_status = self._wait(volume, 'in-use')
        if not wait_status:
            print
            self._clean_up()
            msg = 'Unable to attach volume'
            raise EC2UploadImgException(msg)

        return device

    # ---------------------------------------------------------------------
    def _change_mount_point_permissions(self, target, permissions):
        """Change the permissions of the given target to the given value"""
        command = 'chmod %s %s' % (permissions, target)
        result = self._execute_ssh_command(command)

        return 1

    # ---------------------------------------------------------------------
    def _check_image_exists(self):
        """Check if an image with the given name already exists"""
        my_images = self.ec2.get_all_images(owners='self')
        for image in my_images:
            if image.name == self.image_name:
                msg = 'Image with name "%s" already exists' % self.image_name
                raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _clean_up(self, end_connection=True):
        """Clean up the given resources"""
        if self.instance_ids:
            self.ec2.terminate_instances(instance_ids=self.instance_ids)
        if self.created_volumes:
            for volume in self.created_volumes:
                self._detach_volume(volume, True)
                self._remove_volume(volume)
        if end_connection:
            self._disconnect_from_ec2()

        self.created_volumes = []
        self.instance_ids = []

    # ---------------------------------------------------------------------
    def _connect_to_ec2(self):
        """Connect to EC2"""
        ec2 = boto.ec2.connect_to_region(region_name=self.region,
                                         aws_access_key_id=self.access_key,
                                         aws_secret_access_key=self.secret_key)
        if not ec2:
            msg = 'Could not connect to region: %s' % self.region
            raise EC2UploadImgException(msg)

        self.ec2 = ec2

        return 1

    # ---------------------------------------------------------------------
    def _create_block_device_map(self, snapshot):
        """Create a block device map with the given snapshot"""
        # We assume the root image has 1 partition (either case)
        root_device_name = self._determine_root_device()

        if self.backing_store == 'mag':
            backing_store = 'standard'
        else:
            backing_store = 'gp2'

        block_device_type = boto.ec2.blockdevicemapping.EBSBlockDeviceType(
            delete_on_termination=True,
            snapshot_id=snapshot.id,
            size=self.root_volume_size,
            volume_type=backing_store
        )
        block_device_map = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        block_device_map[root_device_name] = block_device_type

        return block_device_map

    # ---------------------------------------------------------------------
    def _create_image_root_volume(self, source):
        """Create a root volume from the image"""
        self._connect_to_ec2()
        self._check_image_exists()
        helper_instance = self._launch_helper_instance()
        self.helper_instance = helper_instance
        store_volume = self._create_storge_volume()
        store_device_id = self._attach_volume(helper_instance, store_volume)
        target_root_volume = self._create_target_root_volume()
        target_root_device_id = self._attach_volume(helper_instance,
                                             target_root_volume)
        self._establish_ssh_connection(helper_instance)
        self._format_storage_volume(store_device_id)
        self._create_storage_filesystem(store_device_id)
        mount_point = self._mount_storage_volume(store_device_id)
        self._change_mount_point_permissions(mount_point, '777')
        image_filename = self._upload_image(mount_point, source)
        raw_image_filename = self._unpack_image(mount_point, image_filename)
        self._dump_root_fs(mount_point, raw_image_filename,
                           target_root_device_id)
        self._execute_ssh_command('umount %s' %mount_point)
        self._end_ssh_session()
        self._detach_volume(target_root_volume)
        self._detach_volume(store_volume)

        return target_root_volume
    
    # ---------------------------------------------------------------------
    def _create_snapshot(self, volume):
        """Create a snapshot from a volume"""
        snapshot = volume.create_snapshot(description=self.image_description)
        if self.verbose:
            print 'Waiting for snapshot creation: ', snapshot.id
        # Snapshot creation can take a long time, double the the timout value
        current_timeout = self.operation_timeout
        self.operation_timeout = self.operation_timeout * 2
        wait_status = self._wait(snapshot, '100%')
        if not wait_status:
            print
            self._clean_up()
            msg = 'Unable to create snapshot'
            raise EC2UploadImgException(msg)

        self.operation_timeout = current_timeout
        return snapshot

    # ---------------------------------------------------------------------
    def _create_storage_filesystem(self, device_id):
        """Create an ext3 filesystem on the storage volume"""
        if self.verbose:
            print 'Creating ext3 filesystem on storage volume'
        filesystem_partition = '%s1' % device_id
        command = 'mkfs -t ext3 %s' % filesystem_partition
        result = self._execute_ssh_command(command)

        return 1

    # ---------------------------------------------------------------------
    def _create_storge_volume(self):
        """Create the volume that will be used to store the image before
           dumping it to the new root volume"""
        return self._create_volume('%s' % self.storage_volume_size)

    # ---------------------------------------------------------------------
    def _create_target_root_volume(self):
        """Create the volume that will be used as the root volume for
           the image we are creating."""
        return self._create_volume('%s' % self.root_volume_size)

    # ---------------------------------------------------------------------
    def _create_volume(self, size):
        """Create a volume"""
        volume = self.ec2.create_volume(size=size,
                                        zone=self.zone,
                                        volume_type='gp2')
        if self.verbose:
            print 'Waiting for volume creation: ', volume.id
        wait_status = self._wait(volume, 'available')
        self.created_volumes.append(volume)
        if not wait_status:
            print
            self._clean_up()
            msg = 'Time out for Volume creation reached, terminating instance'
            msg += ' and deleting volume'
            raise EC2UploadImgException(msg)

        return volume

    # ---------------------------------------------------------------------
    def _detach_volume(self, volume, no_clean_up=False):
        """Detach the given volume"""
        volume.update()
        if volume.status == 'available':
            # Not attached, nothing to do
            return 1

        volume.detach()
        if self.verbose:
            print 'Wait for volume to detach'
        wait_status = self._wait(volume, 'available')
        if not wait_status:
            print
            if not no_clean_up:
                self._clean_up()
            msg = 'Unable to detach volume'
            raise EC2UploadImgException(msg)

        return 1

    # ---------------------------------------------------------------------
    def _determine_root_device(self):
        """Figure out what the root device should be"""
        root_device_name = '/dev/sda'
        if self.image_virt_type == 'hvm':
            root_device_name = '/dev/sda1'

        return root_device_name

    # ---------------------------------------------------------------------
    def _disconnect_from_ec2(self):
        """Disconnect from EC2"""
        if self.ssh_client:
            self.ssh_client.close()
        EC2Utils._disconnect_from_ec2(self)

        return 1

    # ---------------------------------------------------------------------
    def _dump_root_fs(self, image_dir, raw_image_name, target_root_device):
        """Dump the raw image to the target device"""
        if self.verbose:
            print 'Dumping raw image to new target root volume'
        command = 'dd if=%s/%s of=%s bs=32k' % (image_dir,
                                                raw_image_name,
                                                target_root_device)
        result = self._execute_ssh_command(command)

        return 1

    # ---------------------------------------------------------------------
    def _end_ssh_session(self):
        """End the SSH session"""
        if not self.ssh_client:
            return

        self.ssh_client.close()
        del self.ssh_client
        self.ssh_client = None

        return 1

    # ---------------------------------------------------------------------
    def _establish_ssh_connection(self, instance):
        """Connect to the running instance with ssh"""
        if self.verbose:
            print 'Waiting to obtain instance public IP address'
        instance_ip = instance.ip_address
        timeout_counter = 1
        while not instance_ip:
            instance.update()
            instance_ip = instance.ip_address
            if self.verbose:
                print '. ',
                sys.stdout.flush()
            if timeout_counter * self.default_sleep >= self.operation_timeout:
                msg = 'Unable to obtain the instance public IP address'
                raise EC2UploadImgException(msg)
            timeout_counter += 1
        if self.verbose:
            print

        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        if self.verbose:
            print 'Attempt ssh connection'
        ssh_connection = None
        timeout_counter = 1
        while not ssh_connection:
            try:
                ssh_connection = client.connect(
                    key_filename=self.ssh_key_private_key_file,
                    username=self.inst_user_name,
                    hostname=instance_ip
                )
            except:
                if self.verbose:
                    print '. ',
                    sys.stdout.flush()
                time.sleep(self.default_sleep)
                if (
                        timeout_counter * self.default_sleep >=
                        self.operation_timeout):
                    self._clean_up()
                    msg = 'Time out for ssh connection reached, '
                    msg += 'could not connect'
                    raise EC2UploadImgException(msg)
                timeout_counter += 1
            else:
                ssh_connection = True

        self.ssh_client = client

    # ---------------------------------------------------------------------
    def _execute_ssh_command(self, command):
        """Execute a command on the remote machine, on error raise an exception
           return the result of stdout"""
        if self.inst_user_name != 'root':
            command = 'sudo %s' % command

        if not self.ssh_client:
            msg = 'No ssh connection established, cannot execute command'
            raise EC2UploadImgException(msg)

        stdin, stdout, stderr = self.ssh_client.exec_command(command,
                                                             get_pty=True)
        cmd_error = stderr.read()
        if cmd_error:
            self._clean_up()
            msg = 'Execution of "%s" failed with the following error' % command
            msg += '\n%s' % cmd_err
            raise EC2UploadImgException(msg)

        return stdout.read().strip()

    # ---------------------------------------------------------------------
    def _format_storage_volume(self, device_id):
        """Format the storage volume"""

        if self.verbose:
            print 'Formating storage volume'
        parted = self._get_command_from_instance('parted')
        sfdifk = None
        if not parted:
            sfdisk = self._get_command_from_instance('sfdisk')

        if not parted and not sfdisk:
            self._clean_up()
            msg = 'Neither parted nor sfdisk found on target image. '
            msg += 'Need to partition storage device but cannot, exiting.'
            raise EC2UploadImgException(msg)

        if parted:
            command = '%s -s %s mklabel gpt' % (parted, device_id)
            result = self._execute_ssh_command(command)
            blockdev = self._get_command_from_instance('blockdev')
            command = '%s --getsize %s' % (blockdev, device_id)
            size = self._execute_ssh_command(command)
            command = ('%s -s %s unit s mkpart primary 2048 %d' %
                       (parted, device_id, int(size)-100))
            result = self._execute_ssh_command(command)
        else:
            command = 'echo ",,L" > /tmp/partition.txt'
            result = self._execute_ssh_command(command)
            command = '%s %s < /tmp/partition.txt' % (sfdisk, device_id)
            result = self._execute_ssh_command(command)

        return 1

    # ---------------------------------------------------------------------
    def _get_command_from_instance(self, command):
        """Get the location of the given command from the instance"""
        loc_cmd = 'which %s' % command
        location = self._execute_ssh_command(loc_cmd)

        if location.find('which: no') != -1:
            location = ''

        return location

    # ---------------------------------------------------------------------
    def _get_next_disk_id(self):
        """Return the next device name for a storage volume"""
        device = '/dev/sd' + self.device_ids[self.next_device_id]
        self.next_device_id += 1

        return device

    # ---------------------------------------------------------------------
    def _launch_helper_instance(self):
        """Launch the helper instance that is used to create the new image"""
        self._set_zone_to_use()
        reservation = self.ec2.run_instances(
            key_name=self.ssh_key_pair_name,
            image_id=self.launch_ami,
            instance_type=self.launch_ins_type,
            placement=self.zone
        )

        instance = reservation.instances[0]
        if self.verbose:
            print 'Waiting for instance: ', instance.id
        wait_status = self._wait(instance, 'running')
        self.instance_ids.append(instance.id)
        if not wait_status:
            print
            self._clean_up()
            msg = 'Time out for instance creation reached, '
            msg += 'terminating instance'
            raise EC2UploadImgException(msg)

        return instance

    # ---------------------------------------------------------------------
    def _mount_storage_volume(self, device_id):
        """Mount the storage volume"""
        mount_point = '/mnt'
        mount_device = '%s1' % device_id
        command = 'mount %s %s' % (mount_device, mount_point)
        result = self._execute_ssh_command(command)

        return mount_point

    # ---------------------------------------------------------------------
    def _register_image(self, snapshot):
        """Register an image from the given snapshot"""
        block_device_map = self._create_block_device_map(snapshot)
        if self.verbose:
            print 'Registering image'

        root_device_name = self._determine_root_device()
        volume_type = block_device_map[root_device_name].volume_type
        ami = self.ec2.register_image(
            architecture=self.image_arch,
            block_device_map=block_device_map,
            description=self.image_description,
            kernel_id=self.bootkernel,
            name=self.image_name,
            root_device_name=root_device_name,
            sriov_net_support=self.sriov_type,
            virtualization_type=self.image_virt_type
        )

        return ami

    # ---------------------------------------------------------------------
    def _remove_volume(self, volume):
        """Delete the given volume from EC2"""
        self.ec2.delete_volume(volume_id=volume.id)

        return 1

    # ---------------------------------------------------------------------
    def _set_zone_to_use(self):
        """Set the availability zone to use for all operations"""
        zones = self.ec2.get_all_zones()
        self.zone = zones[-1].name

    # ---------------------------------------------------------------------
    def _upload_image(self, target_dir, source):
        """Upload the source file to the instance"""
        filename = source.split(os.sep)[-1]
        sftp = self.ssh_client.open_sftp()
        try:
            if self.verbose:
                print 'Uploading image file: ', source
            sftp_attrs = sftp.put(source,
                                  '%s/%s' % (target_dir, filename),
                                  self._upload_progress)
            if self.verbose:
                print
        except Exception, e:
            self._clean_up()
            raise e

        return filename

    # ---------------------------------------------------------------------
    def _upload_progress(self, transferred_bytes, total_bytes):
        """In verbose mode give an upload progress indicator"""
        if self.verbose:
            percent_complete = (float(transferred_bytes) / total_bytes) * 100
            if percent_complete - self.percent_transferred >= 10:
                print '.',
                sys.stdout.flush()
                self.percent_transferred = percent_complete

        return 1

    # ---------------------------------------------------------------------
    def _unpack_image(self, image_dir, image_filename):
        """Unpack the uploaded image file"""
        if (
                image_filename.find('.tar') != -1 or
                image_filename.find('.tbz') != -1 or
                image_filename.find('.tgz') != -1):
            command = 'tar -C %s -xvf %s/%s' % (image_dir,
                                                image_dir,
                                                image_filename)
            files = self._execute_ssh_command(command).split('\r\n')
        elif image_filename[-2:] == 'xz':
            files = [image_filename]

        raw_image_file = None
        if files:
            # Find the disk image
            for fl in files:
                if fl.strip()[-2:] == 'xz':
                    if self.verbose:
                        print 'Inflating image: ', fl
                    command = 'xz -d %s/%s' % (image_dir, fl)
                    result = self._execute_ssh_command(command)
                    raw_image_file = fl.strip()[:-3]
                    break
                if fl.strip()[-4:] == '.raw':
                    raw_image_file = fl.strip()
                    break
        if not raw_image_file:
            self._clean_up()
            msg = 'Unable to find raw image file with .raw extension'
            raise EC2UploadImgException(msg)

        return raw_image_file

    # ---------------------------------------------------------------------
    def _wait(self, ec2_resource, status_check):
        """Wait for the EC2 resource to be ready"""
        status = ec2_resource.update()
        timeout_counter = 1
        # Sleep first to allow EC2 to catch up to the issued command
        time.sleep(self.default_sleep)
        while status != status_check:
            if self.verbose:
                print '. ',
                sys.stdout.flush()
            time.sleep(self.default_sleep)
            status = ec2_resource.update()
            if timeout_counter * self.default_sleep >= self.operation_timeout:
                return
            timeout_counter += 1
        if self.verbose:
            print

        return 1

    # ---------------------------------------------------------------------
    def create_image(self, source):
        """Create an AMI (Amazon Machine Image) from the given source"""
        snapshot = self.create_snapshot(source)

        ami = self._register_image(snapshot)

        self._disconnect_from_ec2()

        return ami

    # ---------------------------------------------------------------------
    def create_image_use_root_swap(self, source):
        """Creae an AMI (Amazon Machine Image) from the given source using
           the root swap method"""

        target_root_volume = self._create_image_root_volume(source)
        self.ec2.stop_instances(instance_ids=self.instance_ids)
        if self.verbose:
            print 'Waiting for helper instance to stop'
        wait_status = self._wait(self.helper_instance, 'stopped')
        if not wait_status:
            print
            self._clean_up()
            msg = 'Instance did not stop within allotted time'
            raise EC2UploadImgException(msg)

        # Find the current root volume
        my_volumes = self.ec2.get_all_volumes()
        current_root_volume = None
        device_id = None
        for volume in my_volumes:
            if volume.attach_data.instance_id == self.helper_instance.id:
                current_root_volume = volume
                device_id = volume.attach_data.device
                break

        self._detach_volume(current_root_volume)
        self._attach_volume(self.helper_instance, target_root_volume, device_id)
        if self.verbose:
            print 'Creating new image'
        ami = self.helper_instance.create_image(
            name=self.image_name,
            description=self.image_description,
            no_reboot=True)

        new_image = self.ec2.get_all_images(image_ids=[ami])[0]
        if self.verbose:
            print 'Waiting for new image creation'
        wait_status = self._wait(new_image, 'available')
        skip_cleanup = None
        if not wait_status:
            print
            msg = 'Image creation did not complete within allotted time '
            msg += 'skipping clean up'
            print msg
            skip_cleanup = True
        if not skip_cleanup:
            self._clean_up()

        return ami
        
    # ---------------------------------------------------------------------
    def create_snapshot(self, source):
        """Create a snapshot from the given source"""
        if self.verbose:
            print
        root_volume = self._create_image_root_volume(source)
        snapshot = self._create_snapshot(root_volume)
        self._clean_up(False)
        return snapshot
