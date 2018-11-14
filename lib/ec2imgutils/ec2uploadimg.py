# Copyright 2018 SUSE LLC
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

import os
import paramiko
import sys
import threading
import time


from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2UploadImgException


class EC2ImageUploader(EC2ImgUtils):
    """Upload the given image to Amazon EC2"""

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
                 use_grub2=False,
                 use_private_ip=False,
                 verbose=None,
                 vpc_subnet_id='',
                 wait_count=1):
        EC2ImgUtils.__init__(self)

        self.access_key = access_key
        self.backing_store = backing_store
        self.billing_codes = billing_codes
        self.bootkernel = bootkernel
        self.ena_support = ena_support
        self.image_arch = image_arch
        self.image_description = image_description
        self.image_name = image_name
        self.image_virt_type = image_virt_type
        self.inst_user_name = inst_user_name
        self.launch_ami_id = launch_ami
        self.launch_ins_type = launch_inst_type
        self.region = region
        self.root_volume_size = int(root_volume_size)
        self.running_id = running_id
        self.secret_key = secret_key
        self.security_group_ids = security_group_ids
        self.session_token = session_token
        self.sriov_type = sriov_type
        self.ssh_key_pair_name = ssh_key_pair_name
        self.ssh_key_private_key_file = ssh_key_private_key_file
        self.ssh_timeout = ssh_timeout
        self.use_grub2 = use_grub2
        self.use_private_ip = use_private_ip
        self.verbose = verbose
        self.vpc_subnet_id = vpc_subnet_id
        self.wait_count = wait_count

        self.created_volumes = []
        self.default_sleep = 10
        self.device_ids = ['f', 'g', 'h', 'i', 'j']
        self.instance_ids = []
        self.next_device_id = 0
        self.operation_complete = False
        self.percent_transferred = 0
        self.ssh_client = None
        self.storage_volume_size = 2 * self.root_volume_size
        self.aborted = False

    def abort(self):
        """
        Set the abort flag to take appropriate action and stop image creation.
        """
        if self.verbose:
            print(
                "Aborted upload, please wait while AWS resources get cleaned"
                " up. This may take a few minutes!"
            )
        self.aborted = True

    # ---------------------------------------------------------------------
    def _attach_volume(self, volume, device=None):
        """Attach the given volume to the given instance"""
        if self.aborted:
            return
        if not device:
            device = self._get_next_disk_id()
        self._connect().attach_volume(
                VolumeId=volume['VolumeId'],
                InstanceId=self.helper_instance['InstanceId'],
                Device=device)
        if self.verbose:
            print('Wait for volume attachment')
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
            if self.verbose:
                self.progress_timer.cancel()
            repeat_count = self._check_wait_status(
                wait_status,
                error_msg,
                repeat_count
            )

        return device

    # ---------------------------------------------------------------------
    def _change_mount_point_permissions(self, target, permissions):
        """Change the permissions of the given target to the given value"""
        command = 'chmod %s %s' % (permissions, target)
        result = self._execute_ssh_command(command)

        return result

    # ---------------------------------------------------------------------
    def _check_image_exists(self):
        """Check if an image with the given name already exists"""
        my_images = self._get_owned_images()
        for image in my_images:
            if image['Name'] == self.image_name:
                msg = 'Image with name "%s" already exists' % self.image_name
                raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _check_security_groups_exist(self):
        """Check that the specified security groups exist"""
        try:
            self._connect().describe_security_groups(
                GroupIds=self.security_group_ids.split(',')
            )
        except Exception:
            error_msg = 'One or more of the specified security groups '
            error_msg += 'could not be found: %s' % self.security_group_ids
            raise EC2UploadImgException(error_msg)

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
        image = self._connect().describe_images(
            ImageIds=[self.launch_ami_id]
        )['Images'][0]
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
            if self.verbose:
                print()
            if repeat_count == self.wait_count:
                self.operation_complete = True
                if self.verbose:
                    self.progress_timer.cancel()
                time.sleep(self.default_sleep)  # Wait for the thread
                if not skip_cleanup:
                    self._clean_up()
                raise EC2UploadImgException(error_msg)
            repeat_count += 1
            print('Entering wait loop number %d of %d' % (
                repeat_count,
                self.wait_count
            ))
            self.operation_complete = False
            self._show_progress()
        else:
            repeat_count = self.wait_count + 1
            self.operation_complete = True
            if self.verbose:
                self.progress_timer.cancel()
            time.sleep(self.default_sleep)  # Wait for the thread
            if self.verbose:
                print()

        return repeat_count

    # ---------------------------------------------------------------------
    def _clean_up(self):
        """Clean up the given resources"""
        if self.ssh_client:
            self.ssh_client.close()
        if self.instance_ids:
            self._connect().terminate_instances(InstanceIds=self.instance_ids)
            waiter = self._connect().get_waiter('instance_terminated')
            repeat_count = 1
            error_msg = 'Instance did not stop within allotted time'
            while repeat_count <= self.wait_count:
                try:
                    wait_status = waiter.wait(
                        InstanceIds=[self.helper_instance['InstanceId']],
                        Filters=[
                            {
                                'Name': 'instance-state-name',
                                'Values': ['terminated']
                            }
                        ]
                    )
                except Exception:
                    wait_status = 1
                if self.verbose:
                    self.progress_timer.cancel()
                repeat_count = self._check_wait_status(
                    wait_status,
                    error_msg,
                    repeat_count
                )
        if self.created_volumes:
            for volume in self.created_volumes:
                self._detach_volume(volume)
                self._remove_volume(volume)

        self.created_volumes = []
        self.instance_ids = []

    # ---------------------------------------------------------------------
    def _create_block_device_map(self, snapshot):
        """Create a block device map with the given snapshot"""
        if self.aborted:
            return
        # We assume the root image has 1 partition (either case)
        root_device_name = self._determine_root_device()

        if self.backing_store == 'mag':
            backing_store = 'standard'
        else:
            backing_store = 'gp2'

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
        if self.aborted:
            return
        """Create a root volume from the image"""
        self._check_image_exists()
        if self.vpc_subnet_id:
            self._check_subnet_exists()
        if self.security_group_ids:
            self._check_security_groups_exist()
        if self.running_id:
            # When using an already running instance, simply look up this one
            helper_instance = self._get_helper_instance()
        else:
            helper_instance = self._launch_helper_instance()
        self.helper_instance = helper_instance
        store_volume = self._create_storge_volume()
        store_device_id = self._attach_volume(store_volume)
        target_root_volume = self._create_target_root_volume()
        target_root_device_id = self._attach_volume(target_root_volume)
        self._establish_ssh_connection()
        if not self._device_exists(store_device_id):
            store_device_id = self._find_equivalent_device(store_device_id)
        self._format_storage_volume(store_device_id)
        self._create_storage_filesystem(store_device_id)
        mount_point = self._mount_storage_volume(store_device_id)
        self._change_mount_point_permissions(mount_point, '777')
        image_filename = self._upload_image(mount_point, source)
        raw_image_filename = self._unpack_image(mount_point, image_filename)
        self._dump_root_fs(
            mount_point,
            raw_image_filename,
            target_root_device_id
        )
        self._execute_ssh_command('umount %s' % mount_point)
        self._end_ssh_session()
        self._detach_volume(target_root_volume)
        self._detach_volume(store_volume)

        return target_root_volume

    # ---------------------------------------------------------------------
    def _create_snapshot(self, volume):
        """Create a snapshot from a volume"""
        if self.aborted:
            return
        snapshot = self._connect().create_snapshot(
            VolumeId=volume['VolumeId'],
            Description=self.image_description
        )
        if self.verbose:
            print('Waiting for snapshot creation: ', snapshot['SnapshotId'])
        self.operation_complete = False
        self._show_progress()
        waiter = self._connect().get_waiter('snapshot_completed')
        repeat_count = 1
        error_msg = 'Unable to create snapshot'
        while repeat_count <= self.wait_count:
            try:
                wait_status = waiter.wait(
                    SnapshotIds=[snapshot['SnapshotId']],
                    Filters=[
                        {
                            'Name': 'status',
                            'Values': ['completed']
                        }
                    ]
                )
            except Exception:
                wait_status = 1
            if self.verbose:
                self.progress_timer.cancel()
            repeat_count = self._check_wait_status(
                wait_status,
                error_msg,
                repeat_count
            )

        return snapshot

    # ---------------------------------------------------------------------
    def _create_storage_filesystem(self, device_id):
        """Create an ext3 filesystem on the storage volume"""
        if self.verbose:
            print('Creating ext3 filesystem on storage volume')
        filesystem_partition = '%s1' % device_id
        command = 'mkfs -t ext3 %s' % filesystem_partition
        result = self._execute_ssh_command(command)

        return result

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
        if self.aborted:
            return
        volume = self._connect().create_volume(
            Size=int(size),
            AvailabilityZone=self.zone,
            VolumeType='gp2'
        )
        if self.verbose:
            print('Waiting for volume creation: ', volume['VolumeId'])
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
            if self.verbose:
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
        if self.verbose:
            print('Wait for volume to detach')
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
            if self.verbose:
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
        root_device_name = '/dev/sda'
        if self.image_virt_type == 'hvm':
            root_device_name = '/dev/sda1'

        return root_device_name

    # ---------------------------------------------------------------------
    def _device_exists(self, device_id):
        """Verify that the device node can be found on the remote system"""
        command = 'ls %s' % device_id
        result = self._execute_ssh_command(command)

        return device_id == result

    # ---------------------------------------------------------------------
    def _dump_root_fs(self, image_dir, raw_image_name, target_root_device):
        """Dump the raw image to the target device"""
        if self.aborted:
            return
        if self.verbose:
            print('Dumping raw image to new target root volume')
        if not self._device_exists(target_root_device):
            target_root_device = self._find_equivalent_device(
                target_root_device)
        command = 'dd if=%s/%s of=%s bs=32k' % (image_dir,
                                                raw_image_name,
                                                target_root_device)
        result = self._execute_ssh_command(command)

        return result

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
    def _establish_ssh_connection(self):
        """Connect to the running instance with ssh"""
        if self.aborted:
            return
        if self.verbose:
            print('Waiting to obtain instance IP address')
        instance_ip = self.helper_instance.get('PublicIpAddress')
        if self.use_private_ip:
            instance_ip = self.helper_instance.get('PrivateIpAddress')
        timeout_counter = 1
        while not instance_ip:
            instance = self._connect().describe_instances(
                InstanceIds=[self.helper_instance['InstanceId']]
            )['Reservations'][0]['Instances'][0]
            instance_ip = instance.get('PublicIpAddress')
            if self.use_private_ip:
                instance_ip = instance.get('PrivateIpAddress')
            if self.verbose:
                print('. ', end=' ')
                sys.stdout.flush()
            if timeout_counter * self.default_sleep >= self.ssh_timeout:
                msg = 'Unable to obtain the instance IP address'
                raise EC2UploadImgException(msg)
            timeout_counter += 1
        if self.verbose:
            print()
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        if self.verbose:
            print('Attempt ssh connection')
        ssh_connection = None
        timeout_counter = 1
        while not ssh_connection:
            try:
                ssh_connection = client.connect(
                    key_filename=self.ssh_key_private_key_file,
                    username=self.inst_user_name,
                    hostname=instance_ip
                )
            except Exception:
                if self.verbose:
                    print('. ', end=' ')
                    sys.stdout.flush()
                time.sleep(self.default_sleep)
                if (
                        timeout_counter * self.default_sleep >=
                        self.ssh_timeout):
                    self._clean_up()
                    msg = 'Time out for ssh connection reached, '
                    msg += 'could not connect'
                    raise EC2UploadImgException(msg)
                timeout_counter += 1
            else:
                ssh_connection = True
                print()

        self.ssh_client = client

    # ---------------------------------------------------------------------
    def _execute_ssh_command(self, command):
        """Execute a command on the remote machine, on error raise an exception
           return the result of stdout"""
        if self.aborted:
            return
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
            msg += '\n%s' % cmd_error
            raise EC2UploadImgException(msg)

        return stdout.read().strip().decode('utf-8')

    # ---------------------------------------------------------------------
    def _find_equivalent_device(self, device_id):
        """Try and find a device that should be the same device in the
           instance than the one we attached with a given device id."""
        if self.aborted:
            return
        device_letter = device_id[-1]
        expected_name = '/dev/xvd%s' % device_letter
        if self._device_exists(expected_name):
            return expected_name

        self._clean_up()
        msg = 'Could not find disk device in helper instance with path '
        msg += '%s or %s' % (device_id, expected_name)
        raise EC2UploadImgException(msg)

    # ---------------------------------------------------------------------
    def _format_storage_volume(self, device_id):
        """Format the storage volume"""
        if self.aborted:
            return
        if self.verbose:
            print('Formating storage volume')
        parted = self._get_command_from_instance('parted')
        sfdisk = None
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

        return result

    # ---------------------------------------------------------------------
    def _get_command_from_instance(self, command):
        """Get the location of the given command from the instance"""
        if self.aborted:
            return
        loc_cmd = 'which %s' % command
        location = self._execute_ssh_command(loc_cmd)

        if location.find('which: no') != -1:
            location = ''

        return location

    # ---------------------------------------------------------------------
    def _get_helper_instance(self):
        """Returns handle to running instance"""
        self._set_zone_to_use()
        helper_instance = self._connect().describe_instances(
            InstanceIds=[self.running_id])['Reservations'][0]['Instances'][0]
        if helper_instance['State']['Name'] != 'running':
            msg = 'Helper instance %s is not running' % self.running_id
            raise EC2UploadImgException(msg)

        return helper_instance

    # ---------------------------------------------------------------------
    def _get_next_disk_id(self):
        """Return the next device name for a storage volume"""
        device = '/dev/sd' + self.device_ids[self.next_device_id]
        self.next_device_id += 1

        return device

    # ---------------------------------------------------------------------
    def _launch_helper_instance(self):
        """Launch the helper instance that is used to create the new image"""
        if self.aborted:
            return
        self._set_zone_to_use()
        if self.security_group_ids:
            instance = self._connect().run_instances(
                ImageId=self.launch_ami_id,
                MinCount=1,
                MaxCount=1,
                KeyName=self.ssh_key_pair_name,
                InstanceType=self.launch_ins_type,
                Placement={'AvailabilityZone': self.zone},
                SubnetId=self.vpc_subnet_id,
                SecurityGroupIds=self.security_group_ids.split(',')
            )['Instances'][0]
        else:
            instance = self._connect().run_instances(
                ImageId=self.launch_ami_id,
                MinCount=1,
                MaxCount=1,
                KeyName=self.ssh_key_pair_name,
                InstanceType=self.launch_ins_type,
                Placement={'AvailabilityZone': self.zone},
                SubnetId=self.vpc_subnet_id,
            )['Instances'][0]

        self.instance_ids.append(instance['InstanceId'])

        if self.verbose:
            print('Waiting for instance: ', instance['InstanceId'])
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
            if self.verbose:
                self.progress_timer.cancel()
            repeat_count = self._check_wait_status(
                wait_status,
                error_msg,
                repeat_count
            )

        return instance

    # ---------------------------------------------------------------------
    def _mount_storage_volume(self, device_id):
        """Mount the storage volume"""
        mount_point = '/mnt'
        mount_device = '%s1' % device_id
        command = 'mount %s %s' % (mount_device, mount_point)
        self._execute_ssh_command(command)

        return mount_point

    # ---------------------------------------------------------------------
    def _register_image(self, snapshot):
        """Register an image from the given snapshot"""
        if self.aborted:
            return
        block_device_map = self._create_block_device_map(snapshot)
        if self.verbose:
            print('Registering image')

        root_device_name = self._determine_root_device()
        register_args = {
            'Architecture': self.image_arch,
            'BlockDeviceMappings': block_device_map,
            'Description': self.image_description.strip(),
            'EnaSupport': self.ena_support,
            'Name': self.image_name,
            'RootDeviceName': root_device_name,
            'VirtualizationType': self.image_virt_type
        }
        if self.billing_codes:
            register_args['BillingProducts'] = self.billing_codes.split(',')
        if self.image_virt_type == 'paravirtual':
            register_args['KernelId'] = self.bootkernel
        if self.sriov_type:
            register_args['SriovNetSupport'] = self.sriov_type

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

        if self.verbose:
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
    def _upload_image(self, target_dir, source):
        """Upload the source file to the instance"""
        if self.aborted:
            return
        filename = source.split(os.sep)[-1]
        sftp = self.ssh_client.open_sftp()
        try:
            if self.verbose:
                print('Uploading image file: ', source)
            sftp.put(source,
                     '%s/%s' % (target_dir, filename),
                     self._upload_progress)
            if self.verbose:
                print()
        except Exception as e:
            self._clean_up()
            raise e

        return filename

    # ---------------------------------------------------------------------
    def _upload_progress(self, transferred_bytes, total_bytes):
        """In verbose mode give an upload progress indicator"""
        if self.verbose:
            percent_complete = (float(transferred_bytes) / total_bytes) * 100
            if percent_complete - self.percent_transferred >= 10:
                print('.', end=' ')
                sys.stdout.flush()
                self.percent_transferred = percent_complete

        return 1

    # ---------------------------------------------------------------------
    def _unpack_image(self, image_dir, image_filename):
        """Unpack the uploaded image file"""
        if self.aborted:
            return
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
                        print('Inflating image: ', fl)
                    command = 'xz -d %s/%s' % (image_dir, fl)
                    self._execute_ssh_command(command)
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
    def create_image(self, source):
        """Create an AMI (Amazon Machine Image) from the given source"""
        snapshot = self.create_snapshot(source)

        ami = self._register_image(snapshot)

        return ami

    # ---------------------------------------------------------------------
    def create_image_use_root_swap(self, source):
        """Creae an AMI (Amazon Machine Image) from the given source using
           the root swap method"""

        self._check_virt_type_consistent()
        target_root_volume = self._create_image_root_volume(source)
        self._connect().stop_instances(InstanceIds=self.instance_ids)
        if self.verbose:
            print('Waiting for helper instance to stop')
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
            if self.verbose:
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
        if self.verbose:
            print('Creating new image')
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

        if self.verbose:
            print('Waiting for new image creation')
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
            if self.verbose:
                self.progress_timer.cancel()
            repeat_count = self._check_wait_status(
                wait_status,
                error_msg,
                repeat_count,
                True
            )

        return ami['ImageId']

    # ---------------------------------------------------------------------
    def create_snapshot(self, source):
        """Create a snapshot from the given source"""
        if self.verbose:
            print()
        root_volume = self._create_image_root_volume(source)
        snapshot = self._create_snapshot(root_volume)
        self._clean_up()
        return snapshot
