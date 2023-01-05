#!/usr/bin/python3
#
# Copyright (c) 2015 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of ec2utils
#
# ec2utils is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# ec2utils is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2utils. If not, see
# <http://www.gnu.org/licenses/>.
#

# import datetime
# import dateutil.relativedelta
import logging
import pytest
# import time

from unittest.mock import patch, MagicMock, call

import ec2imgutils.ec2uploadimg as ec2upimg

from ec2imgutils.ec2imgutilsExceptions import (
    EC2UploadImgException
)

logger = logging.getLogger('ec2imgutils')
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
def test_instantiation_sriov_error():
    with pytest.raises(EC2UploadImgException) as e:
        # Instance creation
        ec2upimg.EC2ImageUploader(
            access_key='',
            wait_count=1,
            log_callback=logger,
            sriov_type='mySriovType'
        )
    # Assertions
    msg = 'sriov_type can only be None or simple'
    assert msg in str(e)


# -----------------------------------------------------------------------------
def test_instantiation_tpm_error():
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.abort()
    uploader._attach_volume("volume")
    # Assertions
    assert uploader.aborted is True


# -----------------------------------------------------------------------------
def test_attach_volume_aborted():
    with pytest.raises(EC2UploadImgException) as e:
        # Instance creation
        ec2upimg.EC2ImageUploader(
            access_key='',
            wait_count=1,
            log_callback=logger,
            tpm_support='v3.0'
        )
    # Assertions
    msg = "tpm_support must be one of ['2.0', 'v2.0']"
    assert msg in str(e)


# -----------------------------------------------------------------------------
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_attach_volume_without_device(
    ec2connect_mock,
    show_progress_mock,
    check_wait_status_mock,
    caplog
):
    # mocks
    def log_args(**kwargs):
        logger.info(str(kwargs))

    ec2 = MagicMock()
    ec2.attach_volume.return_value = True
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger,
        running_id='myRunningId'
    )
    uploader.default_sleep = 0.1
    uploader.wait_count = 0

    helper_instance = {
        'State': {
            'Name': 'Running'
        },
        'SubnetId': 'mySubnetId',
        'InstanceId': 'myInstanceId'
    }
    uploader.helper_instance = helper_instance

    volume = {
        'VolumeId': 'myVolumeId'
    }
    uploader._attach_volume(volume)

    # asserts
    ec2.attach_volume.assert_called_once_with(
        VolumeId='myVolumeId',
        InstanceId='myInstanceId',
        Device='/dev/sdf'
    )
    ec2.get_waiter.assert_called_once_with('volume_in_use')
    ec2.get_waiter().wait.assert_not_called()


# -----------------------------------------------------------------------------
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_attach_volume_wait_exception(
    ec2connect_mock,
    _clean_up_mock,
    caplog
):
    # mocks
    def log_args(**kwargs):
        logger.info(str(kwargs))

    ec2 = MagicMock()

    waiter = MagicMock()
    waiter.wait.side_effect = [Exception('MyException'), 1]

    ec2.get_waiter.side_effect = [waiter]

    helper_instance = {
        'State': {
            'Name': 'Running'
        },
        'SubnetId': 'mySubnetId',
        'InstanceId': 'myInstanceId'
    }

    ec2.describe_instances.return_value = helper_instance
    subnets = {
        'Subnets': [
            {
                'AvailabilityZone': 'myAvailabilityZone'
            }
        ]
    }
    ec2.describe_subnets.return_value = subnets
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger,
        running_id='myRunningId'
    )
    uploader.default_sleep = 0.1
    uploader.wait_count = 2
    uploader.helper_instance = helper_instance
    volume = {
        'VolumeId': 'myVolumeId'
    }
    with pytest.raises(EC2UploadImgException) as e:
        uploader._attach_volume(volume, '/dev/sd2')

    # asserts
    ec2.attach_volume.assert_called_once_with(
        VolumeId='myVolumeId',
        InstanceId='myInstanceId',
        Device='/dev/sd2'
    )
    ec2.get_waiter.assert_called_once_with('volume_in_use')
    ec2.attach_volume.assert_called_once_with(
        VolumeId='myVolumeId',
        InstanceId='myInstanceId',
        Device='/dev/sd2'
    )
    msg = "Unable to attach volume"
    assert msg in str(e)


# -----------------------------------------------------------------------------
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_attach_volume(
    ec2connect_mock,
    caplog
):
    # mocks
    def log_args(**kwargs):
        logger.info(str(kwargs))

    ec2 = MagicMock()

    waiter = MagicMock()
    waiter.wait.return_value = None

    ec2.get_waiter.return_value = waiter

    helper_instance = {
        'State': {
            'Name': 'Running'
        },
        'SubnetId': 'mySubnetId',
        'InstanceId': 'myInstanceId'
    }

    ec2.describe_instances.return_value = helper_instance
    subnets = {
        'Subnets': [
            {
                'AvailabilityZone': 'myAvailabilityZone'
            }
        ]
    }
    ec2.describe_subnets.return_value = subnets
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger,
        running_id='myRunningId'
    )
    uploader.default_sleep = 0.1
    uploader.helper_instance = helper_instance
    volume = {
        'VolumeId': 'myVolumeId'
    }
    uploader._attach_volume(volume, '/dev/sd2')

    # asserts
    ec2.attach_volume.assert_called_once_with(
        VolumeId='myVolumeId',
        InstanceId='myInstanceId',
        Device='/dev/sd2'
    )
    ec2.get_waiter.assert_called_once_with('volume_in_use')
    ec2.get_waiter().wait.assert_called_once_with(
        VolumeIds=['myVolumeId'],
        Filters=[{
            'Name': 'attachment.status',
            'Values': ['attached']
        }]
    )


def test_execute_ssh_command(
    caplog
):

    # Mocks
    ssh_client_mock = MagicMock()
    stdin_mock = MagicMock()
    stdin_mock.read.response_value = ''
    stdout_mock = MagicMock()
    stdout_mock.read.return_value = bytearray('stdout', 'utf-8')
    stderr_mock = MagicMock()
    stderr_mock.read.return_value = ''
    ssh_client_mock.exec_command.return_value = (
        stdin_mock,
        stdout_mock,
        stderr_mock
    )

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client_mock
    command = 'example command'
    response = uploader._execute_ssh_command(command)

    # assertions
    assert response == 'stdout'
    stderr_mock.read.assert_has_calls([call()])
    stdout_mock.read.assert_has_calls([call()])
    ssh_client_mock.assert_has_calls([
        call.__bool__(),
        call.exec_command('sudo example command', get_pty=True)
    ])


def test_execute_ssh_command_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True
    uploader.backing_store = 'mag'

    bdm = uploader._execute_ssh_command("myCommand")

    # assertions
    assert bdm is None


def test_execute_ssh_command_without_connection(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = False
    uploader.backing_store = 'mag'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._execute_ssh_command("myCommand")

    # assertions
    msg = 'No ssh connection established, cannot execute command'
    assert msg in str(e)


def test_change_mount_point_permissions(
    caplog
):
    # mocks
    ssh_client_mock = MagicMock()
    stdin_mock = MagicMock()
    stdin_mock.read.response_value = ''
    stdout_mock = MagicMock()
    stdout_mock.read.return_value = bytearray('stdout', 'utf-8')
    stderr_mock = MagicMock()
    stderr_mock.read.return_value = ''
    ssh_client_mock.exec_command.return_value = (
        stdin_mock,
        stdout_mock,
        stderr_mock
    )

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client_mock
    response = uploader._change_mount_point_permissions(
        "target",
        "permissions"
    )

    # assertions
    assert response == 'stdout'
    stderr_mock.read.assert_has_calls([call()])
    stdout_mock.read.assert_has_calls([call()])
    ssh_client_mock.assert_has_calls([
        call.__bool__(),
        call.exec_command('sudo chmod permissions target', get_pty=True)
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_owned_images')
def test_check_image_exists(
    get_owned_images_mock,
    caplog
):
    # Mocks
    images = [
        {
            'Name': 'default'
        }
    ]
    get_owned_images_mock.return_value = images

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.image_name = 'default'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_image_exists()

    # assertions
    msg = 'Image with name "default" already exists'
    assert msg in str(e)
    get_owned_images_mock.assert_has_calls([call()])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_check_security_groups_exist(
    ec2connect_mock,
    caplog
):

    # Mocks
    ec2 = MagicMock()
    ec2.describe_security_groups.side_effect = Exception("except")
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.security_group_ids = 'securityGroupId'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_security_groups_exist()

    # assertions
    msg = 'One or more of the specified security groups '
    msg += 'could not be found: securityGroupId'
    assert msg in str(e)
    ec2.assert_has_calls([
        call.describe_security_groups(GroupIds=['securityGroupId'])
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_check_subnet_exist(
    ec2connect_mock,
    caplog
):
    # Mocks
    ec2 = MagicMock()
    ec2.describe_subnets.side_effect = Exception("except")
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.vpc_subnet_id = 'subnetId'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_subnet_exists()

    # assertions
    msg = 'Specified subnet subnetId not found'
    assert msg in str(e)
    ec2.assert_has_calls([
        call.describe_subnets(SubnetIds=['subnetId'])
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_check_virt_type_consistent1(
    ec2connect_mock,
    caplog
):
    # Mocks
    ec2 = MagicMock()
    images = {
        'Images': [
            {
                'VirtualizationType': 'virtualizationType'
            }
        ]
    }
    ec2.describe_images.return_value = images
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.launch_ami_id = 'launchAmiId'
    uploader.image_virt_type = 'virtualizationType2'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_virt_type_consistent()

    # assertions
    msg = 'Virtualization type of the helper image and the '
    msg += 'target image must be the same when using '
    msg += 'root-swap method for image creation.'
    assert msg in str(e)

    ec2.assert_has_calls([
        call.describe_images(ImageIds=['launchAmiId'])
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_check_virt_type_consistent2(
    ec2connect_mock,
    caplog
):
    # Mocks
    ec2 = MagicMock()
    instances = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'State': {
                            'Name': 'running'
                        },
                        'SubnetId': 'subnetId',
                        'VirtualizationType': 'myVirtualizationType',
                        'ImageId': 'myImageId'
                    }
                ]
            }
        ]
    }
    ec2.describe_instances.return_value = instances
    subnets = {
        'Subnets': [
            {
                'AvailabilityZone': 'myAvailabilityZone'
            }
        ]

    }
    ec2.describe_subnets.return_value = subnets
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.running_id = 'myRunningId'
    uploader.image_virt_type = 'anotherVirtType'

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_virt_type_consistent()

    # assertions
    assert uploader.zone == 'myAvailabilityZone'

    msg = 'Virtualization type of the helper image and the '
    msg += 'target image must be the same when using '
    msg += 'root-swap method for image creation.'
    assert msg in str(e)


def test_check_virt_type_consistent3(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.launch_ami_id = None
    uploader.running_id = None

    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_virt_type_consistent()

    # assertions
    msg = 'Could not determine helper image virtualization '
    msg += 'type necessary for root swap method'
    assert msg in str(e)


def test_check_wait_status1(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.default_sleep = 0.1
    repeat_count = uploader._check_wait_status(
        None,
        'error_msg',
        0
    )

    uploader.wait_count = 1
    # assertions
    assert repeat_count == 2


def test_check_wait_status2(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.wait_count = 1
    uploader.default_sleep = 0.1
    with pytest.raises(EC2UploadImgException) as e:
        uploader._check_wait_status(
            'wait_status',
            'error_msg',
            1
        )

    # assertions
    assert uploader.operation_complete is True
    assert 'error_msg' in str(e)


def test_check_wait_status3(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.wait_count = 3
    uploader.default_sleep = 0.1
    repeat_count = uploader._check_wait_status(
        'wait_status',
        'error_msg',
        1
    )
    # assertions
    assert repeat_count == 2
    assert uploader.operation_complete is False


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up(
    ec2connect_mock,
    caplog
):

    # Mocks
    ssh_client = MagicMock()
    ssh_client.close.return_value = None

    ec2 = MagicMock()
    ec2.terminate_instances.return_value = None
    ec2.get_waiter().wait.return_value = None
    ec2connect_mock.return_value = ec2

    helper_instance = {
        'InstanceId': 'myInstanceId'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client
    uploader.instance_ids = 'instance1,instance2'
    uploader.default_sleep = 0.1
    uploader.created_volumes = None
    uploader.wait_count = 2
    uploader.helper_instance = helper_instance

    uploader._clean_up()

    # assertions
    ec2.assert_has_calls([
        call.terminate_instances(InstanceIds='instance1,instance2'),
        call.get_waiter('instance_terminated'),
        call.get_waiter().wait(
            InstanceIds=['myInstanceId'],
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['terminated']
            }]
        )
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_volumes(
    ec2connect_mock,
    caplog
):

    # Mocks
    ssh_client = MagicMock()
    ssh_client.close.return_value = None

    ec2 = MagicMock()
    ec2.terminate_instances.return_value = None
    ec2.delete_volume.return_value = None
    volumes = {
        'Volumes': [
            {
                'State': 'available',
                'VolumeId': 'myVolumeId'
            }
        ]
    }
    ec2.describe_volumes.return_value = volumes

    ec2.get_waiter().wait.return_value = None
    ec2connect_mock.return_value = ec2

    helper_instance = {
        'InstanceId': 'myInstanceId'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client
    uploader.instance_ids = 'instance1,instance2'
    uploader.default_sleep = 0.1
    volumes2 = [
        {
            'VolumeId': 'Vol1'
        }
    ]
    uploader.created_volumes = volumes2
    uploader.wait_count = 1
    uploader.helper_instance = helper_instance

    uploader._clean_up()

    # assertions
    ec2.assert_has_calls([
        call.terminate_instances(InstanceIds='instance1,instance2'),
        call.get_waiter('instance_terminated'),
        call.get_waiter().wait(
            InstanceIds=['myInstanceId'],
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['terminated']
            }]
        ),
        call.describe_volumes(VolumeIds=['Vol1']),
        call.delete_volume(VolumeId='Vol1')
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_wait_exception(
    ec2connect_mock,
    caplog
):

    # Mocks
    ssh_client = MagicMock()
    ssh_client.close.return_value = None

    ec2 = MagicMock()
    ec2.terminate_instances.return_value = None

    ec2.get_waiter().wait.side_effect = [Exception("myException")]

    ec2connect_mock.return_value = ec2

    helper_instance = {
        'InstanceId': 'myInstanceId'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client
    uploader.instance_ids = 'instance1,instance2'
    uploader.default_sleep = 0.1
    uploader.created_volumes = None
    uploader.wait_count = 2
    uploader.helper_instance = helper_instance
    with pytest.raises(EC2UploadImgException) as e:
        uploader._clean_up()

    # assertions
    ec2.assert_has_calls([
        call.terminate_instances(InstanceIds='instance1,instance2'),
        call.get_waiter('instance_terminated'),
        call.get_waiter().wait(
            InstanceIds=['myInstanceId'],
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['terminated']
            }]
        )
    ])
    msg = 'Instance did not stop within allotted time'
    assert msg in str(e)


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_block_device_map(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.backing_store = 'mag'

    bdm = uploader._create_block_device_map({'SnapshotId': 'mySnapshotId'})

    # assertions
    assert bdm[0]['DeviceName'] == '/dev/sda1'
    assert bdm[0]['Ebs']['SnapshotId'] == 'mySnapshotId'
    assert bdm[0]['Ebs']['VolumeSize'] == 10
    assert bdm[0]['Ebs']['DeleteOnTermination'] is True
    assert bdm[0]['Ebs']['VolumeType'] == 'standard'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_block_device_map2(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.backing_store = 'ssd'

    bdm = uploader._create_block_device_map({'SnapshotId': 'mySnapshotId'})

    # assertions
    assert bdm[0]['DeviceName'] == '/dev/sda1'
    assert bdm[0]['Ebs']['SnapshotId'] == 'mySnapshotId'
    assert bdm[0]['Ebs']['VolumeSize'] == 10
    assert bdm[0]['Ebs']['DeleteOnTermination'] is True
    assert bdm[0]['Ebs']['VolumeType'] == 'gp2'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_block_device_map3(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.backing_store = 'myBackingStore'

    bdm = uploader._create_block_device_map({'SnapshotId': 'mySnapshotId'})

    # assertions
    assert bdm[0]['DeviceName'] == '/dev/sda1'
    assert bdm[0]['Ebs']['SnapshotId'] == 'mySnapshotId'
    assert bdm[0]['Ebs']['VolumeSize'] == 10
    assert bdm[0]['Ebs']['DeleteOnTermination'] is True
    assert bdm[0]['Ebs']['VolumeType'] == 'myBackingStore'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_block_device_map_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True
    uploader.backing_store = 'mag'

    bdm = uploader._create_block_device_map({'SnapshotId': 'mySnapshotId'})

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._detach_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._end_ssh_session')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._dump_root_fs')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._unpack_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._upload_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._change_mount_point_permissions')  # noqa: E501
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._mount_storage_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_storage_filesystem')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._format_storage_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_target_root_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._find_device_name')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._establish_ssh_connection')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._attach_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_storage_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_security_groups_exist')  # noqa: E501
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_subnet_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_image_root_volume(
    ec2connect_mock,
    check_image_exists_mock,
    check_subnet_exists_mock,
    check_security_groups_exist_mock,
    get_helper_instance_mock,
    create_storage_volume_mock,
    attach_volume_mock,
    establish_ssh_connection_mock,
    find_device_name_mock,
    create_target_root_volume_mock,
    format_storage_volume_mock,
    create_storage_filesystem_mock,
    mount_storage_volume_mock,
    change_mount_point_permissions_mock,
    upload_image_mock,
    unpack_image_mock,
    dump_root_fs_mock,
    execute_ssh_command_mock,
    end_ssh_session_mock,
    detach_volume_mock,
    caplog
):

    # Mocks
    check_image_exists_mock.return_value = None
    check_subnet_exists_mock.return_value = None
    check_security_groups_exist_mock.return_value = None
    get_helper_instance_mock.return_value = None
    create_storage_volume_mock.return_value = 'myStorageVolume'
    attach_volume_mock.return_value = None
    establish_ssh_connection_mock.return_value = None
    find_device_name_mock.side_effect = ['myStoreDeviceId', 'myRootDeviceId']
    create_target_root_volume_mock.return_value = 'myTargetRootVolume'
    format_storage_volume_mock.return_value = None
    create_storage_filesystem_mock.return_value = None
    mount_storage_volume_mock.return_value = 'myMountPoint'
    change_mount_point_permissions_mock.return_value = None
    upload_image_mock.return_value = 'myImageFilename'
    unpack_image_mock.return_value = 'rawImageFilename'
    dump_root_fs_mock.return_value = None
    execute_ssh_command_mock.return_value = None
    end_ssh_session_mock.return_value = None
    detach_volume_mock.return_value = None

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.vpc_subnet_id = 'mySubnetId'
    uploader.security_group_ids = 'mySecurityGroupId'
    uploader.running_id = 'myRunningId'
    uploader.storage_volume_size = '10G'
    uploader.root_volume_size = '20G'
    response = uploader._create_image_root_volume('myImageFilename')

    # assertions
    assert response == 'myTargetRootVolume'
    check_image_exists_mock.assert_called_once_with()
    check_subnet_exists_mock.assert_called_once_with()
    check_security_groups_exist_mock.assert_called_once_with()
    get_helper_instance_mock.assert_called_once_with()
    create_storage_volume_mock.assert_called_once_with()
    attach_volume_mock.assert_has_calls([
        call('myStorageVolume'),
        call('myTargetRootVolume')
    ])
    establish_ssh_connection_mock.assert_called_once_with()
    find_device_name_mock.assert_has_calls([call('10G'), call('20G')])
    create_target_root_volume_mock.assert_called_once_with()
    format_storage_volume_mock.assert_called_once_with('myStoreDeviceId')
    create_storage_filesystem_mock.assert_called_once_with('myStoreDeviceId')
    mount_storage_volume_mock.assert_called_once_with('myStoreDeviceId')
    change_mount_point_permissions_mock.assert_called_once_with(
        'myMountPoint',
        '777'
    )
    upload_image_mock.assert_called_once_with(
        'myMountPoint',
        'myImageFilename'
    )
    unpack_image_mock.assert_called_once_with(
        'myMountPoint',
        'myImageFilename'
    )
    dump_root_fs_mock.assert_called_once_with(
        'myMountPoint',
        'rawImageFilename',
        'myRootDeviceId'
    )
    execute_ssh_command_mock.assert_called_once_with('umount myMountPoint')
    end_ssh_session_mock.assert_called_once_with()
    detach_volume_mock.assert_has_calls([
        call('myTargetRootVolume'),
        call('myStorageVolume')
    ])


def test_create_image_root_volume_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._create_image_root_volume({'SnapshotId': 'mySnapshotId'})

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot(
    ec2connect_mock,
    show_progress_mock,
    check_wait_status_mock,
    caplog
):

    # Mocks
    snapshot = {
        'SnapshotId': 'mySnapshotId'
    }
    ec2 = MagicMock()
    ec2.create_snapshot.return_value = snapshot

    waiter_mock = MagicMock()
    waiter_mock.wait.return_value = None

    ec2.get_waiter.return_value = waiter_mock
    ec2connect_mock.return_value = ec2

    check_wait_status_mock.return_value = 3

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    vol = {
        'VolumeId': 'myVolumeId'
    }
    resp = uploader._create_snapshot(vol)
    uploader.wait_count = 1

    # assertions
    assert resp['SnapshotId'] == snapshot['SnapshotId']
    ec2.assert_has_calls([
        call.create_snapshot(VolumeId='myVolumeId', Description='AWS EC2 AMI'),
        call.get_waiter('snapshot_completed')
    ])


def test_create_snapshot_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._create_snapshot({'VolumeId': 'myVolumeId'})

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_create_storage_filesystem(
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    execute_ssh_command_mock.return_value = 'success'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    result = uploader._create_storage_filesystem('myDeviceId')

    # assertions
    assert result == 'success'
    execute_ssh_command_mock.assert_has_calls([
        call('mkfs -t ext3 myDeviceId1')
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
def test_create_storage_volume(
    create_volume_mock,
    caplog
):
    # Mocks
    create_volume_mock.return_value = 'myStorageVolume'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.storage_volume_size = 99
    result = uploader._create_storage_volume()

    # assertions
    assert result == 'myStorageVolume'
    create_volume_mock.assert_has_calls([call('99')])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
def test_create_target_root_volume(
    create_volume_mock,
    caplog
):
    # Mocks
    create_volume_mock.return_value = 'myStorageVolume'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.root_volume_size = 99
    result = uploader._create_target_root_volume()

    # assertions
    assert result == 'myStorageVolume'
    create_volume_mock.assert_has_calls([call('99')])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_volume(
    ec2connect_mock,
    show_progress_mock,
    check_wait_status_mock,
    caplog
):

    # Mocks
    ec2 = MagicMock()
    volume = {
        'VolumeId': 'myVolumeId'
    }
    ec2.create_volume.return_value = volume

    waiter_mock = MagicMock()
    waiter_mock.wait.return_value = None

    ec2.get_waiter.return_value = waiter_mock
    ec2connect_mock.return_value = ec2

    check_wait_status_mock.return_value = 3

    # function calls
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.zone = 'myZone'
    resp = uploader._create_volume('10')

    # assertions
    assert resp['VolumeId'] == 'myVolumeId'
    assert uploader.created_volumes[-1]['VolumeId'] == 'myVolumeId'
    ec2connect_mock.assert_has_calls([
        call(),
        call().create_volume(
            Size=10,
            AvailabilityZone='myZone',
            VolumeType='gp2'
        ),
        call(),
        call().get_waiter('volume_available'),
        call().get_waiter().wait(
            VolumeIds=['myVolumeId'],
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
    ])
    show_progress_mock.assert_has_calls([call()])
    check_wait_status_mock.assert_has_calls(
        [
            call(
                None,
                'Time out for Volume creation reached, terminating instance and deleting volume',  # noqa: E501
                1
            )
        ]
    )


def test_create_volume_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._create_volume('10G')

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_detach_volume(
    ec2connect_mock,
    show_progress_mock,
    check_wait_status_mock,
    caplog
):

    # Mocks
    ec2 = MagicMock()
    volumes = {
        'Volumes': [
            {
                'VolumeId': 'myVolumeId',
                'State': 'notAvailable'
            }
        ]
    }
    ec2.describe_volumes.return_value = volumes
    ec2.detach_volume.return_value = None

    waiter_mock = MagicMock()
    waiter_mock.wait.return_value = None

    ec2.get_waiter.return_value = waiter_mock
    ec2connect_mock.return_value = ec2

    check_wait_status_mock.return_value = 3

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.zone = 'myZone'
    vol = {
        'VolumeId': 'myVolumeId'
    }
    resp = uploader._detach_volume(vol)

    # assertions
    assert resp == 1
    ec2connect_mock.assert_has_calls([
        call(),
        call().describe_volumes(VolumeIds=['myVolumeId']),
        call(),
        call().detach_volume(VolumeId='myVolumeId'),
        call(),
        call().get_waiter('volume_available'),
        call().get_waiter().wait(
            VolumeIds=['myVolumeId'],
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
    ])
    show_progress_mock.assert_has_calls([call()])
    check_wait_status_mock.assert_has_calls([
        call(None, 'Unable to detach volume', 1)
    ])


def test_detach_volume_none(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._detach_volume(None)

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_device_exists(
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    execute_ssh_command_mock.return_value = 'myDeviceId'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    result = uploader._device_exists('myDeviceId')

    # assertions
    assert result is True
    execute_ssh_command_mock.assert_has_calls([call('ls myDeviceId')])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_dump_root_fs(
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    execute_ssh_command_mock.return_value = 'success'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    result = uploader._dump_root_fs(
        'myImageDir',
        'rawImageName',
        'targetRootDevice'
    )

    # assertions
    assert result == 'success'
    execute_ssh_command_mock.assert_has_calls([
        call('dd if=myImageDir/rawImageName of=targetRootDevice bs=32k')
    ])


def test_dump_root_fs_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._dump_root_fs(
        "image_dir",
        "raw_image_name",
        "target_root_device"
    )

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_end_ssh_session_not_ssh_client(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = None
    result = uploader._end_ssh_session()
    assert result is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_end_ssh_session_ssh_client(
    caplog
):
    # Mocks
    ssh_client_mock = MagicMock()
    ssh_client_mock.close.return_value = None

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client_mock
    result = uploader._end_ssh_session()

    # assertions
    assert result == 1


@patch('ec2imgutils.ec2uploadimg.paramiko.WarningPolicy')
@patch('ec2imgutils.ec2uploadimg.paramiko.client')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_establish_ssh_connection(
    ec2connect_mock,
    paramiko_client_mock,
    paramiko_warning_pol_mock,
    caplog
):
    # Mocks
    ssh_client = MagicMock()
    warningPolicy_mock = MagicMock()
    paramiko_warning_pol_mock.return_value = warningPolicy_mock
    paramiko_client_mock.response_value = ssh_client

    instances = {
        'Reservations': [{
            'Instances': [
                {
                    'State': {
                        'Name': 'Running'
                    },
                    'SubnetId': 'mySubnetId',
                    'InstanceId': 'myInstanceId',
                    'PublicIpAddress': '1.2.3.4',
                }
            ]
        }]
    }
    ec2connect_mock.describe_instances.return_value = instances

    helper_instance = {
        'PublicIpAddress': '1.2.3.4'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.helper_instance = helper_instance
    uploader._establish_ssh_connection()

    # assertions
    paramiko_client_mock.assert_has_calls([
        call.SSHClient(),
        call.SSHClient().set_missing_host_key_policy(warningPolicy_mock),
        call.SSHClient().connect(
            key_filename=None,
            username=None,
            hostname='1.2.3.4',
            timeout=10
        ),
    ])


def test_establish_ssh_connection_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True
    uploader.backing_store = 'mag'

    bdm = uploader._establish_ssh_connection()

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_find_device_name(
    execute_command_mock,
    caplog
):
    # Mocks
    lsbk_resp = '''{
        "blockdevices": [
            {
                "size": "10G",
                "name": "myDeviceName"
            }
        ]
    }'''

    execute_command_mock.return_value = lsbk_resp

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    resp = uploader._find_device_name(10)

    # assertions
    assert resp == '/dev/myDeviceName'
    execute_command_mock.assert_has_calls([call('lsblk -a -J')])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_command_from_instance')
def test_format_storage_volume(
    get_command_mock,
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    get_command_mock.side_effect = ['parted', 'blockdev']
    execute_ssh_command_mock.side_effect = ['parted', '1000', 'result']

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    resp = uploader._format_storage_volume('myDeviceId')

    # assertions
    assert resp == 'result'
    get_command_mock.assert_has_calls([call('parted'), call('blockdev')])
    execute_ssh_command_mock.assert_has_calls([
        call('parted -s myDeviceId mklabel gpt'),
        call('blockdev --getsize myDeviceId'),
        call('parted -s myDeviceId unit s mkpart primary 2048 900')
    ])


def test_format_storage_volume_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._format_storage_volume("myDeviceId")

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_get_command_from_instance(
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    execute_ssh_command_mock.side_effect = ['/usr/bin/gparted']

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    resp = uploader._get_command_from_instance('gparted')

    # assertions
    assert resp == '/usr/bin/gparted'
    execute_ssh_command_mock.assert_has_calls([call('which gparted')])


def test_get_command_from_instance_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._get_command_from_instance("myDeviceId")

    # assertions
    assert bdm is None


def test_get_next_disk_id(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.next_device_id = 2
    uploader.device_ids = ['0', '1', '2', '3', '4']
    resp = uploader._get_next_disk_id()

    # assertions
    assert resp == '/dev/sd2'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._set_zone_to_use')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_launch_helper_instance(
    ec2connect_mock,
    set_zone_mock,
    show_progress_mock,
    caplog
):

    # Mocks
    ec2 = MagicMock()
    instances = {
        'Instances': [
            {
                'InstanceId': 'myInstanceId'
            }
        ]
    }
    ec2.run_instances.return_value = instances
    waiter = MagicMock()
    waiter.wait.return_value = None
    ec2.get_waiter.return_value = waiter
    ec2connect_mock.return_value = ec2

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.zone = 'myZone'
    uploader.launch_ami_id = 'launchAmiId'
    uploader.ssh_key_pair_name = 'keyPairName'
    uploader.launch_ins_type = 'instanceType'
    uploader.use_private_ip = False
    uploader.vpc_subnet_id = 'mySubnetId'
    uploader.wait_count = 0

    resp = uploader._launch_helper_instance()

    # assertions
    assert resp['InstanceId'] == 'myInstanceId'

    ec2connect_mock.assert_has_calls([
        call(),
        call().run_instances(
            ImageId='launchAmiId',
            MinCount=1,
            MaxCount=1,
            KeyName='keyPairName',
            InstanceType='instanceType',
            Placement={'AvailabilityZone': 'myZone'},
            NetworkInterfaces=[{
                'DeviceIndex': 0,
                'AssociatePublicIpAddress': True,
                'SubnetId': 'mySubnetId'
            }],
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{
                    'Key': 'Name',
                    'Value': 'ec2uploadimg-helper-instance'
                }]
            }]
        ),
        call(),
        call().get_waiter('instance_running')
    ])
    set_zone_mock.assert_has_calls([call()])
    show_progress_mock.assert_has_calls([call()])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_mount_storage_volume(
    execute_ssh_command_mock,
    caplog
):
    # Mocks
    execute_ssh_command_mock.side_effect = [None]

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    result = uploader._mount_storage_volume('sda')

    # assertions
    assert result == '/mnt'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._determine_root_device')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_block_device_map')
def test_register_image(
    create_block_device_map_mock,
    determine_root_device_mock,
    ec2connect_mock,
    caplog
):
    # Mocks
    create_block_device_map_mock.side_effect = ['blockDeviceMap']
    determine_root_device_mock.side_effect = ['rootDevice']

    ami = {
        'ImageId': 'myImageId'
    }

    ec2connect_mock().register_image.side_effect = [ami]

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.billing_codes = 'billingCode1,billingCode2'
    uploader.boot_mode = 'uefi'
    uploader.image_virt_type = 'paravirtual'
    uploader.bootkernel = 'myBootKernel'
    uploader.tmp = 'tmpVersion'

    response = uploader._register_image('snapshot')

    # assertions
    assert response == 'myImageId'

    create_block_device_map_mock.assert_has_calls([call('snapshot')])
    determine_root_device_mock.assert_has_calls([call()])
    ec2connect_mock.assert_has_calls([
        call(),
        call(),
        call().register_image(
            Architecture='x86_64',
            BlockDeviceMappings='blockDeviceMap',
            Description='AWS EC2 AMI',
            EnaSupport=False,
            Name='default',
            RootDeviceName='rootDevice',
            VirtualizationType='paravirtual',
            BillingProducts=['billingCode1', 'billingCode2'],
            BootMode='uefi',
            KernelId='myBootKernel'
        )
    ])


def test_register_image_aborted(
    caplog
):
    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True

    bdm = uploader._register_image("mySnapshot")

    # assertions
    assert bdm is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_remove_volume(
    ec2connect_mock,
    caplog
):
    # Mocks
    ec2connect_mock().delete_volume.side_effect = None

    volume = {
        'VolumeId': 'myVolumeId'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader._remove_volume(volume)

    # assertions
    assert response == 1
    ec2connect_mock.assert_has_calls([
        call(),
        call(),
        call().delete_volume(VolumeId='myVolumeId')
    ])


def test_remove_volume_empty(
    caplog
):
    # Mocks

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader._remove_volume(None)

    # assertions
    assert response is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_set_zone_to_use(
    ec2connect_mock,
    caplog
):
    # Mocks
    ec2connect_mock().delete_volume.side_effect = None

    volume = {
        'VolumeId': 'myVolumeId'
    }

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader._remove_volume(volume)

    # assertions
    assert response == 1
    ec2connect_mock.assert_has_calls([
        call(),
        call(),
        call().delete_volume(VolumeId='myVolumeId')
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._upload_progress')
def test_upload_image(
    upload_progress_mock,
    caplog
):
    # Mocks
    ssh_client_mock = MagicMock()
    sftp_mock = MagicMock()
    sftp_mock.put.side_effect = [None]
    ssh_client_mock().open_sftp.side_effect = [sftp_mock]

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.ssh_client = ssh_client_mock

    response = uploader._upload_image('targetDir', '/test/imageName.img')

    # assertions
    assert response == 'imageName.img'
    ssh_client_mock.assert_has_calls([
        call(),
        call.open_sftp(),
        call.open_sftp().put(
            '/test/imageName.img',
            'targetDir/imageName.img',
            upload_progress_mock
        )
    ])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._execute_ssh_command')
def test_unpack_image(
    execute_ssh_command_mock,
    clean_up_mock,
    caplog
):
    # Mocks
    files = 'fileName1.xz\r\nfilename2.xz'

    execute_ssh_command_mock.return_value = files

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader._unpack_image('imageDir', 'imageFilename.tgz')

    # assertions
    assert response == 'fileName1'
    execute_ssh_command_mock.assert_has_calls([
        call('tar -C imageDir -xvf imageDir/imageFilename.tgz'),
        call('xz -d imageDir/fileName1.xz')
    ])


def test_unpack_image_aborted(
    caplog
):
    # Mocks

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.aborted = True
    response = uploader._unpack_image("image_dir", "image_filename")

    # assertions
    assert response is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._register_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader.create_snapshot')
def test_create_image(
    create_snapshot_mock,
    register_image_mock,
    caplog
):
    # Mocks
    create_snapshot_mock.return_value = 'snapshot'
    register_image_mock.return_value = 'myAMI1'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader.create_image('source')

    # assertions
    assert response == 'myAMI1'
    create_snapshot_mock.assert_has_calls([call('source')])
    register_image_mock.assert_has_calls([call('snapshot')])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._register_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_image_from_snapshot(
    ec2connect_mock,
    register_image_mock,
    caplog
):
    # Mocks
    snapshots = {
        'Snapshots': [
            {
                'name': 'snapshot1'
            }
        ]
    }
    ec2connect_mock.describe_snapshots.return_value = snapshots
    register_image_mock.return_value = 'ami1'

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    response = uploader.create_image_from_snapshot('source')

    # assertions
    assert response == 'ami1'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._attach_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._detach_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_image_root_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
def test_create_image_use_root_swap(
    check_virt_type_consistent_mock,
    create_root_volume_mock,
    connect_mock,
    show_progress_mock,
    detach_volume_mock,
    attach_volume_mock,
    caplog
):
    # Mocks
    create_root_volume_mock.return_value = 'targetRootVol'
    connect_mock.stop_instances.return_value = None
    waiter = MagicMock()
    connect_mock.get_waiter.return_value = waiter
    volumes = [
        {
            'Attachments': [
                {
                    'InstanceId': 'myInstanceId',
                    'Device': 'myDevice'
                }
            ]
        }
    ]
    connect_mock.describe_volumes.return_value = volumes
    instances = {
        'Reservations': [{
            'Instances': [
                {
                    'State': {
                        'Name': 'Running'
                    },
                    'SubnetId': 'mySubnetId',
                    'InstanceId': 'myInstanceId',
                    'PublicIpAddress': '1.2.3.4',
                    'BlockDeviceMappings': [
                        {
                            'DeviceName': 'myDeviceName',
                            'Ebs': {
                                'DeleteOnTermination': True
                            }
                        }
                    ]
                }
            ]
        }]
    }
    connect_mock.describe_instances.return_value = instances
    ami = {
        'ImageId': 'imageId1'
    }
    connect_mock().create_image.return_value = ami

    # Instance creation
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.wait_count = 0
    helper_instance = {
        'InstanceId': 'myInstanceId'
    }
    uploader.helper_instance = helper_instance
    response = uploader.create_image_use_root_swap('source')

    # assertions
    assert response == 'imageId1'

    check_virt_type_consistent_mock.assert_has_calls([call()])
    create_root_volume_mock.assert_has_calls([call('source')])
    show_progress_mock.assert_has_calls([call(), call()])
    detach_volume_mock.assert_has_calls([call(None)])
    attach_volume_mock.assert_has_calls([call('targetRootVol', None)])
