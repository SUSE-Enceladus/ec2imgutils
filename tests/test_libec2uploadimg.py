#!/usr/bin/python3
#
# Copyright (c) 2023 SUSE Linux GmbH.  All rights reserved.
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

import base64
import boto3
import botocore.config
import botocore.exceptions
import hashlib
import inspect
import logging
import lzma
import os
import pytest
import sys
import tarfile
import threading


from botocore.stub import Stubber
from unittest.mock import ANY, patch, MagicMock, call

# Load the module from the source tree not the one on the system
test_path = os.path.abspath(
    os.path.dirname(inspect.getfile(inspect.currentframe())))
code_path = os.path.abspath('%s/../lib' % test_path)
sys.path.insert(0, code_path)

import ec2imgutils.ec2uploadimg as ec2upimg  # noqa: E402
from ec2imgutils.ec2imgutilsExceptions import (  # noqa: E402
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
def test_attach_volume_aborted():
    uploader = ec2upimg.EC2ImageUploader(
        access_key='',
        wait_count=1,
        log_callback=logger
    )
    uploader.abort()
    uploader._attach_volume("volume", "/dev/sda1")
    # Assertions
    assert uploader.aborted is True


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
    assert bdm[0]['Ebs']['VolumeType'] == 'gp3'


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


# -----------------------------------------------------------------------------
# Tests for the upload using the EBS direct APIs
BLOCK_SIZE = 524288


class FakeEBS:
    """Stand-in for the boto3 ebs client"""

    def __init__(self, block_size=BLOCK_SIZE, fail_on_put=None,
                 on_put=None):
        self.block_size = block_size
        self.fail_on_put = fail_on_put
        self.on_put = on_put
        self.blocks = {}
        self.started = []
        self.completed = []
        self.lock = threading.Lock()

    def start_snapshot(self, **kwargs):
        self.started.append(kwargs)
        return {'SnapshotId': 'snap-1234', 'BlockSize': self.block_size}

    def put_snapshot_block(self, **kwargs):
        if self.on_put:
            self.on_put()
        if kwargs['BlockIndex'] == self.fail_on_put:
            raise RuntimeError('put failed')
        with self.lock:
            self.blocks[kwargs['BlockIndex']] = kwargs

    def complete_snapshot(self, **kwargs):
        self.completed.append(kwargs)
        return {'Status': 'pending'}


def _make_uploader(**kwargs):
    kwargs.setdefault('access_key', '')
    kwargs.setdefault('wait_count', 1)
    kwargs.setdefault('log_callback', logger)
    return ec2upimg.EC2ImageUploader(**kwargs)


def _sha(data):
    return hashlib.sha256(data).digest()


def _b64(digest):
    return base64.b64encode(digest).decode()


def _raw_image_data():
    """3 blocks and a bit, the second block is all zeros"""
    block0 = b'\x01' * BLOCK_SIZE
    block1 = bytes(BLOCK_SIZE)
    block2 = b'\x02' * BLOCK_SIZE
    tail = b'\x03' * 100
    return block0, block1, block2, tail


def _write_raw_image(path):
    data = b''.join(_raw_image_data())
    path.write_bytes(data)
    return data


def test_instantiation_upload_workers_error():
    with pytest.raises(EC2UploadImgException) as exc:
        _make_uploader(upload_workers=0)
    assert 'upload_workers' in str(exc.value)
    with pytest.raises(EC2UploadImgException):
        _make_uploader(upload_workers='many')


def test_instantiation_upload_workers():
    assert _make_uploader().upload_workers == 8
    assert _make_uploader(upload_workers='3').upload_workers == 3


def _tar_with(path, members, mode='w'):
    with tarfile.open(path, mode) as tar:
        for name, content in members:
            with open(path.parent / 'member.tmp', 'wb') as tmp:
                tmp.write(content)
            tar.add(path.parent / 'member.tmp', arcname=name)


@pytest.mark.parametrize('kind', [
    'raw', 'xz', 'tar_raw', 'tgz_raw', 'tar_xz', 'tar_xz_compressed'
])
def test_open_raw_image(tmp_path, kind):
    data = b'raw image data' * 100
    if kind == 'raw':
        source = tmp_path / 'image.raw'
        source.write_bytes(data)
    elif kind == 'xz':
        source = tmp_path / 'image.raw.xz'
        source.write_bytes(lzma.compress(data))
    elif kind == 'tar_raw':
        source = tmp_path / 'image.tar'
        _tar_with(source, [('README', b'x'), ('image.raw', data)])
    elif kind == 'tgz_raw':
        source = tmp_path / 'image.tgz'
        _tar_with(source, [('image.raw', data)], 'w:gz')
    elif kind == 'tar_xz':
        source = tmp_path / 'image.tar'
        _tar_with(source, [('image.raw.xz', lzma.compress(data))])
    else:
        source = tmp_path / 'image.tar.xz'
        _tar_with(source, [('image.raw', data)], 'w:xz')

    uploader = _make_uploader()
    with uploader._open_raw_image(str(source)) as stream:
        assert stream.read() == data


@pytest.mark.parametrize('name,is_tar', [
    ('image.qcow2', False),
    ('image.tar', True)
])
def test_open_raw_image_no_raw_file(tmp_path, name, is_tar):
    source = tmp_path / name
    if is_tar:
        _tar_with(source, [('README', b'nothing to see')])
    else:
        source.write_bytes(b'data')

    uploader = _make_uploader()
    with pytest.raises(EC2UploadImgException) as exc:
        with uploader._open_raw_image(str(source)):
            pass
    assert 'Unable to find raw image file' in str(exc.value)


def test_upload_snapshot_blocks(tmp_path):
    source = tmp_path / 'image.raw'
    block0, block1, block2, tail = _raw_image_data()
    _write_raw_image(source)
    ebs = FakeEBS()

    uploader = _make_uploader(upload_workers=2)
    digests = uploader._upload_snapshot_blocks(
        ebs, 'snap-1234', BLOCK_SIZE, str(source)
    )

    # The all zero block is skipped, the last block is padded
    assert sorted(ebs.blocks) == [0, 2, 3]
    assert sorted(digests) == [0, 2, 3]
    padded_tail = tail + bytes(BLOCK_SIZE - len(tail))
    for index, data in ((0, block0), (2, block2), (3, padded_tail)):
        put = ebs.blocks[index]
        assert put['SnapshotId'] == 'snap-1234'
        assert put['BlockData'] == data
        assert put['DataLength'] == BLOCK_SIZE
        assert put['Checksum'] == _b64(_sha(data))
        assert put['ChecksumAlgorithm'] == 'SHA256'
        assert digests[index] == _sha(data)


def test_upload_snapshot_blocks_many_blocks(tmp_path):
    # More blocks than in flight limit to exercise the wait loop
    source = tmp_path / 'image.raw'
    source.write_bytes(
        b''.join(bytes([i + 1]) * 1024 for i in range(50))
    )
    ebs = FakeEBS(block_size=1024)

    uploader = _make_uploader(upload_workers=2)
    digests = uploader._upload_snapshot_blocks(
        ebs, 'snap-1234', 1024, str(source)
    )

    assert sorted(digests) == list(range(50))
    assert sorted(ebs.blocks) == list(range(50))


def test_upload_snapshot_blocks_too_large(tmp_path):
    source = tmp_path / 'image.raw'
    source.write_bytes(b'\x01' * 3000)
    ebs = FakeEBS(block_size=1024)

    uploader = _make_uploader()
    # Root volume of 2048 bytes
    uploader.root_volume_size = 2048 / 1024 ** 3
    with pytest.raises(EC2UploadImgException) as exc:
        uploader._upload_snapshot_blocks(
            ebs, 'snap-1234', 1024, str(source)
        )
    assert 'larger than the root volume size' in str(exc.value)


def test_upload_snapshot_blocks_exact_fit(tmp_path):
    source = tmp_path / 'image.raw'
    source.write_bytes(b'\x01' * 2048)
    ebs = FakeEBS(block_size=1024)

    uploader = _make_uploader()
    uploader.root_volume_size = 2048 / 1024 ** 3
    digests = uploader._upload_snapshot_blocks(
        ebs, 'snap-1234', 1024, str(source)
    )
    assert sorted(digests) == [0, 1]


def test_upload_snapshot_blocks_put_failure(tmp_path):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS(fail_on_put=2)

    uploader = _make_uploader(upload_workers=1)
    with pytest.raises(RuntimeError):
        uploader._upload_snapshot_blocks(
            ebs, 'snap-1234', BLOCK_SIZE, str(source)
        )


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._wait_for_snapshot')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
def test_create_snapshot_matches_ebs_api_model(
    check_image_exists_mock,
    wait_for_snapshot_mock,
    tmp_path
):
    """Run against a real boto3 ebs client whose responses are stubbed,
       botocore validates all parameters against the API model"""
    source = tmp_path / 'image.raw'
    block0, block1, block2, tail = _raw_image_data()
    _write_raw_image(source)
    padded_tail = tail + bytes(BLOCK_SIZE - len(tail))

    ebs = boto3.client(
        'ebs',
        region_name='us-east-1',
        aws_access_key_id='key',
        aws_secret_access_key='secret'
    )
    stubber = Stubber(ebs)
    stubber.add_response(
        'start_snapshot',
        {'SnapshotId': 'snap-1234', 'BlockSize': BLOCK_SIZE},
        {
            'VolumeSize': 10,
            'Description': 'AWS EC2 AMI',
            'ClientToken': ANY,
            'Timeout': ec2upimg.SNAPSHOT_TIMEOUT_MINUTES
        }
    )
    digests = []
    for index, data in ((0, block0), (2, block2), (3, padded_tail)):
        digests.append(_sha(data))
        stubber.add_response(
            'put_snapshot_block',
            {},
            {
                'SnapshotId': 'snap-1234',
                'BlockIndex': index,
                'BlockData': data,
                'DataLength': BLOCK_SIZE,
                'Checksum': _b64(_sha(data)),
                'ChecksumAlgorithm': 'SHA256'
            }
        )
    stubber.add_response(
        'complete_snapshot',
        {'Status': 'pending'},
        {
            'SnapshotId': 'snap-1234',
            'ChangedBlocksCount': 3,
            'Checksum': _b64(_sha(b''.join(digests))),
            'ChecksumAlgorithm': 'SHA256',
            'ChecksumAggregationMethod': 'LINEAR'
        }
    )

    uploader = _make_uploader(upload_workers=1)
    with stubber, patch.object(uploader, '_connect', return_value=ebs):
        snapshot = uploader.create_snapshot(str(source))

    assert snapshot == {'SnapshotId': 'snap-1234'}
    stubber.assert_no_pending_responses()


def test_complete_snapshot():
    ebs = FakeEBS()
    uploader = _make_uploader()
    uploader.pending_snapshot_id = 'snap-1234'
    # Intentionally not in order, the checksum is based on the index order
    digests = {5: _sha(b'five'), 0: _sha(b'zero'), 2: _sha(b'two')}

    uploader._complete_snapshot(ebs, 'snap-1234', digests)

    expected = _sha(_sha(b'zero') + _sha(b'two') + _sha(b'five'))
    assert ebs.completed == [{
        'SnapshotId': 'snap-1234',
        'ChangedBlocksCount': 3,
        'Checksum': _b64(expected),
        'ChecksumAlgorithm': 'SHA256',
        'ChecksumAggregationMethod': 'LINEAR'
    }]
    assert uploader.pending_snapshot_id is None


def test_complete_snapshot_no_blocks():
    ebs = FakeEBS()
    uploader = _make_uploader()
    uploader._complete_snapshot(ebs, 'snap-1234', {})
    assert ebs.completed[0]['ChangedBlocksCount'] == 0
    assert ebs.completed[0]['Checksum'] == _b64(_sha(b''))


def test_start_snapshot():
    ebs = FakeEBS()
    uploader = _make_uploader(root_volume_size=12, image_description='desc')

    snapshot_id, block_size = uploader._start_snapshot(ebs)

    assert snapshot_id == 'snap-1234'
    assert block_size == BLOCK_SIZE
    assert uploader.pending_snapshot_id == 'snap-1234'
    start = ebs.started[0]
    assert start['VolumeSize'] == 12
    assert start['Description'] == 'desc'
    assert start['Timeout'] == ec2upimg.SNAPSHOT_TIMEOUT_MINUTES
    assert start['ClientToken']


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._wait_for_snapshot')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_ebs_direct(
    connect_mock,
    check_image_exists_mock,
    wait_for_snapshot_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS()
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader(upload_workers=3)
    snapshot = uploader.create_snapshot(str(source))

    assert snapshot == {'SnapshotId': 'snap-1234'}
    check_image_exists_mock.assert_called_once_with()
    wait_for_snapshot_mock.assert_called_once_with('snap-1234')
    assert sorted(ebs.blocks) == [0, 2, 3]
    assert ebs.completed[0]['ChangedBlocksCount'] == 3
    assert uploader.pending_snapshot_id is None
    # The sealed snapshot must not be deleted
    ec2.delete_snapshot.assert_not_called()
    # The EBS client gets one connection per worker
    ebs_call = [
        c for c in connect_mock.call_args_list
        if c[1].get('service') == 'ebs'
    ][0]
    assert ebs_call[1]['config'].max_pool_connections == 3


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_ebs_direct_upload_failure(
    connect_mock,
    check_image_exists_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS(fail_on_put=0)
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader(upload_workers=1)
    with pytest.raises(RuntimeError):
        uploader.create_snapshot(str(source))

    assert not ebs.completed
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    assert uploader.pending_snapshot_id is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_ebs_direct_too_large(
    connect_mock,
    check_image_exists_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    source.write_bytes(b'\x01' * 3000)
    ebs = FakeEBS(block_size=1024)
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader()
    uploader.root_volume_size = 2048 / 1024 ** 3
    with pytest.raises(EC2UploadImgException):
        uploader.create_snapshot(str(source))

    assert not ebs.completed
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_ebs_direct_abort_during_upload(
    connect_mock,
    check_image_exists_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    uploader = _make_uploader(upload_workers=1)
    ebs = FakeEBS(on_put=uploader.abort)
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    snapshot = uploader.create_snapshot(str(source))

    assert snapshot is None
    assert not ebs.completed
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')


def test_create_snapshot_ebs_direct_aborted():
    uploader = _make_uploader()
    uploader.aborted = True

    assert uploader._create_snapshot_from_image('source') is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_delete_pending_snapshot(connect_mock):
    ec2 = MagicMock()
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.pending_snapshot_id = 'snap-1234'

    uploader._delete_pending_snapshot()

    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    assert uploader.pending_snapshot_id is None

    # Nothing pending, nothing to do
    uploader._delete_pending_snapshot()
    ec2.delete_snapshot.assert_called_once()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_delete_pending_snapshot_error(connect_mock, caplog):
    ec2 = MagicMock()
    ec2.delete_snapshot.side_effect = Exception('nope')
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.pending_snapshot_id = 'snap-1234'

    uploader._delete_pending_snapshot()

    assert 'Unable to delete incomplete snapshot snap-1234' in caplog.text


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_deletes_pending_snapshot(connect_mock):
    ec2 = MagicMock()
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.pending_snapshot_id = 'snap-1234'

    uploader._clean_up()

    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    ec2.terminate_instances.assert_not_called()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_wait_for_snapshot(
    connect_mock,
    show_progress_mock,
    check_wait_status_mock
):
    ec2 = MagicMock()
    connect_mock.return_value = ec2
    check_wait_status_mock.return_value = 3

    uploader = _make_uploader()
    uploader._wait_for_snapshot('snap-1234')

    ec2.get_waiter.assert_called_once_with('snapshot_completed')
    ec2.get_waiter().wait.assert_called_once_with(
        SnapshotIds=['snap-1234'],
        Filters=[{'Name': 'status', 'Values': ['completed']}]
    )


def test_wait_for_snapshot_aborted():
    uploader = _make_uploader()
    uploader.aborted = True

    assert uploader._wait_for_snapshot('snap-1234') is None


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_ebs_service(boto3_mock):
    uploader = _make_uploader(region='us-east-1')
    config = botocore.config.Config(read_timeout=5)

    client = uploader._connect(service='ebs', config=config)

    session = boto3_mock.session.Session.return_value
    session.client.assert_called_once_with(
        aws_access_key_id='',
        aws_secret_access_key=None,
        region_name='us-east-1',
        service_name='ebs',
        config=config
    )
    assert client == session.client.return_value


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_ebs_service_session_token(boto3_mock):
    uploader = _make_uploader(region='us-east-1', session_token='token')

    client = uploader._connect(service='ebs')

    boto3_mock.client.assert_called_once_with(
        aws_access_key_id='',
        aws_secret_access_key=None,
        aws_session_token='token',
        region_name='us-east-1',
        service_name='ebs'
    )
    assert client == boto3_mock.client.return_value


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_defaults_to_ec2(boto3_mock):
    uploader = _make_uploader(region='us-east-1')

    uploader._connect()

    session = boto3_mock.session.Session.return_value
    assert session.client.call_args[1]['service_name'] == 'ec2'
    assert 'config' not in session.client.call_args[1]


def test_connect_ebs_config():
    uploader = _make_uploader(region='us-east-1', upload_workers=5)
    with patch.object(uploader, '_connect') as connect_mock:
        uploader._connect_ebs()
    kwargs = connect_mock.call_args[1]
    assert kwargs['service'] == 'ebs'
    assert kwargs['config'].max_pool_connections == 5
    assert kwargs['config'].retries['mode'] == 'standard'
    assert kwargs['config'].retries['max_attempts'] == 2
    assert kwargs['config'].connect_timeout == ec2upimg.CONNECT_TIMEOUT
    assert kwargs['config'].read_timeout == 300


def test_connect_ebs_config_upload_timeout():
    uploader = _make_uploader(region='us-east-1', upload_timeout=900)
    with patch.object(uploader, '_connect') as connect_mock:
        uploader._connect_ebs()
    assert connect_mock.call_args[1]['config'].read_timeout == 900


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
            VirtualizationType='hvm',
            BillingProducts=['billingCode1', 'billingCode2'],
            BootMode='uefi'
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


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._tag_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._register_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader.create_snapshot')
def test_create_image_aborted(
    create_snapshot_mock,
    register_image_mock,
    tag_image_mock
):
    create_snapshot_mock.return_value = None

    uploader = _make_uploader()

    assert uploader.create_image('source') is None
    register_image_mock.assert_not_called()
    tag_image_mock.assert_not_called()


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


def test_invalid_tpm_value():
    with pytest.raises(EC2UploadImgException) as e:
        # Instance creation
        ec2upimg.EC2ImageUploader(
            access_key='',
            wait_count=1,
            log_callback=logger,
            tpm_support='1'
        )
    msg = "tpm_support must be one of ['2.0', 'v2.0']"
    assert msg in str(e)


def test_invalid_imds_value():
    with pytest.raises(EC2UploadImgException) as e:
        # Instance creation
        ec2upimg.EC2ImageUploader(
            access_key='',
            wait_count=1,
            log_callback=logger,
            imds_support='1'
        )
    msg = "imds_support must be one of ['2.0', 'v2.0']"
    assert msg in str(e)


# -----------------------------------------------------------------------------
# Tests for the retry of writing blocks and the related options
def test_instantiation_upload_retries_and_timeout():
    uploader = _make_uploader()
    assert uploader.upload_retries == 8
    assert uploader.upload_timeout == 300
    uploader = _make_uploader(upload_retries='3', upload_timeout='45')
    assert uploader.upload_retries == 3
    assert uploader.upload_timeout == 45


@pytest.mark.parametrize('option', ['upload_retries', 'upload_timeout'])
@pytest.mark.parametrize('value', [0, -1, 'many', None])
def test_instantiation_upload_retries_and_timeout_error(option, value):
    with pytest.raises(EC2UploadImgException) as exc:
        _make_uploader(**{option: value})
    assert option in str(exc.value)


def _client_error(code=None, status=400, message='failed'):
    error = {'Message': message}
    if code:
        error['Code'] = code
    else:
        error['Code'] = str(status)
    return botocore.exceptions.ClientError(
        {
            'Error': error,
            'ResponseMetadata': {
                'HTTPStatusCode': status,
                'RequestId': 'req-1'
            }
        },
        'PutSnapshotBlock'
    )


class FlakyEBS:
    """Raises the given errors for the first calls, then succeeds"""

    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def put_snapshot_block(self, **kwargs):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)


@pytest.fixture
def no_sleep():
    with patch('ec2imgutils.ec2uploadimg.time.sleep') as sleep_mock:
        yield sleep_mock


@pytest.mark.parametrize('error', [
    _client_error(),
    _client_error(status=400, message=''),
    _client_error('RequestThrottledException'),
    _client_error('ThrottlingException'),
    _client_error('ConcurrentLimitExceededException'),
    _client_error('InternalServerException', 500),
    _client_error('ServiceUnavailable', 503),
    botocore.exceptions.ReadTimeoutError(endpoint_url='https://ebs'),
    botocore.exceptions.ConnectTimeoutError(endpoint_url='https://ebs'),
    botocore.exceptions.ConnectionClosedError(endpoint_url='https://ebs'),
    botocore.exceptions.EndpointConnectionError(endpoint_url='https://ebs'),
    ConnectionResetError('reset'),
    TimeoutError('timed out')
])
def test_put_snapshot_block_retries(error, no_sleep, caplog):
    ebs = FlakyEBS([error, error])
    uploader = _make_uploader(upload_retries=3)

    result = uploader._put_snapshot_block(ebs, 'snap-1234', 7, b'data')

    assert result == (7, _sha(b'data'))
    assert ebs.calls == 3
    assert caplog.text.count('Writing block 7 failed') == 2
    assert 'attempt 2 of 3' in caplog.text


def test_put_snapshot_block_logs_details(no_sleep, caplog):
    ebs = FlakyEBS([_client_error()])
    uploader = _make_uploader()

    uploader._put_snapshot_block(ebs, 'snap-1234', 1, b'data')

    assert 'HTTP status 400' in caplog.text
    assert 'request id req-1' in caplog.text


@pytest.mark.parametrize('code,status', [
    ('ValidationException', 400),
    ('AccessDeniedException', 403),
    ('ResourceNotFoundException', 404),
    ('ServiceQuotaExceededException', 402)
])
def test_put_snapshot_block_no_retry(code, status, no_sleep):
    error = _client_error(code, status)
    ebs = FlakyEBS([error, error])
    uploader = _make_uploader()

    with pytest.raises(botocore.exceptions.ClientError):
        uploader._put_snapshot_block(ebs, 'snap-1234', 1, b'data')

    assert ebs.calls == 1
    no_sleep.assert_not_called()


def test_put_snapshot_block_other_exception_no_retry(no_sleep):
    ebs = FlakyEBS([RuntimeError('bug')])
    uploader = _make_uploader()

    with pytest.raises(RuntimeError):
        uploader._put_snapshot_block(ebs, 'snap-1234', 1, b'data')

    assert ebs.calls == 1


def test_put_snapshot_block_attempts_exhausted(no_sleep):
    ebs = FlakyEBS([_client_error()] * 10)
    uploader = _make_uploader(upload_retries=4)

    with pytest.raises(EC2UploadImgException) as exc:
        uploader._put_snapshot_block(ebs, 'snap-1234', 9, b'data')

    assert ebs.calls == 4
    assert 'block 9' in str(exc.value)
    assert 'snap-1234' in str(exc.value)
    assert '4 attempt(s)' in str(exc.value)


def test_put_snapshot_block_single_attempt(no_sleep):
    ebs = FlakyEBS([_client_error()])
    uploader = _make_uploader(upload_retries=1)

    with pytest.raises(EC2UploadImgException):
        uploader._put_snapshot_block(ebs, 'snap-1234', 1, b'data')

    assert ebs.calls == 1
    no_sleep.assert_not_called()


def test_put_snapshot_block_aborted_stops_retrying(no_sleep):
    uploader = _make_uploader(upload_retries=5)
    ebs = FlakyEBS([_client_error()] * 5)
    ebs_put = ebs.put_snapshot_block

    def put_and_abort(**kwargs):
        uploader.abort()
        return ebs_put(**kwargs)

    ebs.put_snapshot_block = put_and_abort

    with pytest.raises(EC2UploadImgException):
        uploader._put_snapshot_block(ebs, 'snap-1234', 1, b'data')

    assert ebs.calls == 1


@pytest.mark.parametrize('attempt,limit', [
    (1, 4), (2, 8), (3, 16), (4, 32), (5, 60), (20, 60)
])
def test_wait_before_retry_backoff_limit(attempt, limit):
    uploader = _make_uploader()
    with patch('ec2imgutils.ec2uploadimg.random.uniform') as uniform_mock:
        uniform_mock.return_value = 0
        uploader._wait_before_retry(attempt)
    uniform_mock.assert_called_once_with(0, limit)


def test_wait_before_retry_sleeps_in_steps(no_sleep):
    uploader = _make_uploader()
    with patch(
        'ec2imgutils.ec2uploadimg.random.uniform', return_value=2.5
    ):
        uploader._wait_before_retry(1)
    assert [c[0][0] for c in no_sleep.call_args_list] == [1, 1, 0.5]


def test_wait_before_retry_aborted(no_sleep):
    uploader = _make_uploader()
    uploader.aborted = True
    with patch('ec2imgutils.ec2uploadimg.random.uniform', return_value=30):
        uploader._wait_before_retry(1)
    no_sleep.assert_not_called()


def test_upload_snapshot_blocks_recovers_from_errors(tmp_path, no_sleep):
    source = tmp_path / 'image.raw'
    block0, block1, block2, tail = _raw_image_data()
    _write_raw_image(source)
    ebs = FakeEBS()
    original_put = ebs.put_snapshot_block
    failures = {0: 2, 2: 1}

    def flaky_put(**kwargs):
        index = kwargs['BlockIndex']
        if failures.get(index):
            failures[index] -= 1
            raise _client_error()
        return original_put(**kwargs)

    ebs.put_snapshot_block = flaky_put
    uploader = _make_uploader(upload_workers=3, upload_retries=3)

    digests = uploader._upload_snapshot_blocks(
        ebs, 'snap-1234', BLOCK_SIZE, str(source)
    )

    assert sorted(digests) == [0, 2, 3]
    assert sorted(ebs.blocks) == [0, 2, 3]
    assert digests[0] == _sha(block0)
    assert digests[2] == _sha(block2)


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_retries_exhausted_deletes_snapshot(
    connect_mock,
    check_image_exists_mock,
    tmp_path,
    no_sleep
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS()

    def always_400(**kwargs):
        raise _client_error()

    ebs.put_snapshot_block = always_400
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader(upload_workers=1, upload_retries=2)
    with pytest.raises(EC2UploadImgException):
        uploader.create_snapshot(str(source))

    assert not ebs.completed
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')


# -----------------------------------------------------------------------------
# Tests for the dropped para-virtual support
def test_determine_root_device():
    assert _make_uploader()._determine_root_device() == '/dev/sda1'


@pytest.mark.parametrize('virt_type', ['paravirtual', 'para', 'other'])
def test_instantiation_virt_type_error(virt_type):
    with pytest.raises(EC2UploadImgException) as exc:
        _make_uploader(image_virt_type=virt_type)
    assert 'Only hvm images are supported' in str(exc.value)


def test_instantiation_virt_type_hvm(caplog):
    uploader = _make_uploader(image_virt_type='hvm')
    assert uploader.image_virt_type == 'hvm'
    assert 'deprecated' not in caplog.text


@pytest.mark.parametrize('argument', [
    {'bootkernel': 'aki-1'}, {'use_grub2': True}
])
def test_instantiation_deprecated_arguments(argument, caplog):
    uploader = _make_uploader(**argument)
    assert 'deprecated and ignored' in caplog.text
    assert uploader.image_virt_type == 'hvm'


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_register_image_never_sends_kernel(connect_mock):
    connect_mock().register_image.return_value = {'ImageId': 'ami-1'}
    uploader = _make_uploader(bootkernel='aki-1')

    uploader._register_image({'SnapshotId': 'snap-1'})

    kwargs = connect_mock().register_image.call_args[1]
    assert kwargs['VirtualizationType'] == 'hvm'
    assert kwargs['RootDeviceName'] == '/dev/sda1'
    assert 'KernelId' not in kwargs


def test_constructor_accepts_all_previous_arguments():
    """The signature of the uploader is backwards compatible"""
    _make_uploader(
        access_key='key', backing_store='ssd', billing_codes='code',
        bootkernel=None, config=None, ena_support=False, image_arch='x86_64',
        image_description='desc', image_name='name', image_virt_type='hvm',
        inst_user_name='root', launch_ami='ami-1',
        launch_inst_type='t2.micro', region='us-east-1',
        root_volume_size=10, running_id=None, secret_key='secret',
        security_group_ids='sg-1', session_token=None, sriov_type=None,
        ssh_key_pair_name='key', ssh_key_private_key_file='file',
        ssh_timeout=300, channel_timeout=900, use_grub2=False,
        use_private_ip=False, vpc_subnet_id='subnet-1', use_enclave=False,
        wait_count=1, log_level=logging.INFO, log_callback=logger,
        boot_mode=None, tpm_support=None, imds_support=None, image_tags=None
    )


# -----------------------------------------------------------------------------
# Tests for the root swap method with the EBS direct upload
def _root_swap_uploader(**kwargs):
    kwargs.setdefault('launch_ami', 'ami-donor')
    kwargs.setdefault('launch_inst_type', 't3.micro')
    return _make_uploader(**kwargs)


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_subnet_exists')
def test_create_image_root_volume(
    check_subnet_mock,
    create_snapshot_mock,
    launch_mock,
    create_volume_mock
):
    order = MagicMock()
    order.attach_mock(check_subnet_mock, 'check_subnet')
    order.attach_mock(create_snapshot_mock, 'snapshot')
    order.attach_mock(launch_mock, 'launch')
    order.attach_mock(create_volume_mock, 'volume')
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    launch_mock.return_value = {'InstanceId': 'i-donor'}
    create_volume_mock.return_value = {'VolumeId': 'vol-1'}

    uploader = _root_swap_uploader(
        root_volume_size=12, vpc_subnet_id='subnet-1'
    )
    volume = uploader._create_image_root_volume('source')

    assert volume == {'VolumeId': 'vol-1'}
    assert uploader.helper_instance == {'InstanceId': 'i-donor'}
    # The image is uploaded first, no instance is needed for it
    assert order.mock_calls == [
        call.check_subnet(),
        call.snapshot('source', temporary=True),
        call.launch(),
        call.volume(12, 'snap-1')
    ]


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
def test_create_image_root_volume_running_instance(
    create_snapshot_mock,
    get_helper_mock,
    launch_mock,
    create_volume_mock
):
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    get_helper_mock.return_value = {'InstanceId': 'i-running'}
    create_volume_mock.return_value = {'VolumeId': 'vol-1'}

    uploader = _make_uploader(running_id='i-running')
    uploader._create_image_root_volume('source')

    get_helper_mock.assert_called_once_with()
    launch_mock.assert_not_called()
    assert uploader.helper_instance == {'InstanceId': 'i-running'}
    create_volume_mock.assert_called_once_with(10, 'snap-1')


def test_create_image_root_volume_aborted():
    uploader = _root_swap_uploader()
    uploader.aborted = True
    assert uploader._create_image_root_volume('source') is None


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_subnet_exists')
def test_create_image_root_volume_upload_aborted(
    check_subnet_mock,
    create_snapshot_mock,
    launch_mock,
    create_volume_mock,
    clean_up_mock
):
    create_snapshot_mock.return_value = None

    uploader = _root_swap_uploader()

    assert uploader._create_image_root_volume('source') is None
    launch_mock.assert_not_called()
    create_volume_mock.assert_not_called()
    clean_up_mock.assert_called_once_with()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
def test_create_image_root_volume_aborted_after_upload(
    create_snapshot_mock,
    launch_mock,
    create_volume_mock,
    clean_up_mock
):
    uploader = _root_swap_uploader()

    def upload_and_abort(source, temporary=False):
        uploader.abort()
        return {'SnapshotId': 'snap-1'}

    create_snapshot_mock.side_effect = upload_and_abort

    assert uploader._create_image_root_volume('source') is None
    launch_mock.assert_not_called()
    clean_up_mock.assert_called_once_with()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
def test_create_image_root_volume_aborted_at_launch(
    create_snapshot_mock,
    launch_mock,
    create_volume_mock,
    clean_up_mock
):
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    launch_mock.return_value = None

    uploader = _root_swap_uploader()

    assert uploader._create_image_root_volume('source') is None
    create_volume_mock.assert_not_called()
    clean_up_mock.assert_called_once_with()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
def test_create_image_root_volume_aborted_at_volume(
    create_snapshot_mock,
    launch_mock,
    create_volume_mock,
    clean_up_mock
):
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    launch_mock.return_value = {'InstanceId': 'i-donor'}
    create_volume_mock.return_value = None

    uploader = _root_swap_uploader()

    assert uploader._create_image_root_volume('source') is None
    clean_up_mock.assert_called_once_with()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_image_root_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_image_use_root_swap_aborted(
    connect_mock,
    check_virt_type_mock,
    create_root_volume_mock
):
    create_root_volume_mock.return_value = None

    uploader = _root_swap_uploader()

    assert uploader.create_image_use_root_swap('source') is None
    connect_mock.return_value.stop_instances.assert_not_called()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._wait_for_snapshot')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_subnet_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_image_root_volume_registers_temporary_snapshot(
    connect_mock,
    check_subnet_mock,
    check_image_exists_mock,
    wait_for_snapshot_mock,
    launch_mock,
    create_volume_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS()
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )
    launch_mock.return_value = {'InstanceId': 'i-donor'}
    create_volume_mock.return_value = {'VolumeId': 'vol-1'}

    uploader = _root_swap_uploader(upload_workers=2)
    uploader._create_image_root_volume(str(source))

    assert sorted(ebs.blocks) == [0, 2, 3]
    assert ebs.completed
    assert uploader.temporary_snapshot_ids == ['snap-1234']
    create_volume_mock.assert_called_once_with(10, 'snap-1234')

    # The temporary snapshot is removed with the other resources
    uploader._clean_up()
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    assert uploader.temporary_snapshot_ids == []


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._wait_for_snapshot')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_snapshot_keeps_snapshot_by_default(
    connect_mock,
    check_image_exists_mock,
    wait_for_snapshot_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS()
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader()
    uploader.create_snapshot(str(source))

    assert uploader.temporary_snapshot_ids == []
    ec2.delete_snapshot.assert_not_called()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_deletes_temporary_snapshots(connect_mock, caplog):
    ec2 = MagicMock()
    ec2.delete_snapshot.side_effect = [Exception('nope'), None]
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.temporary_snapshot_ids = ['snap-1', 'snap-2']

    uploader._clean_up()

    assert ec2.delete_snapshot.call_args_list == [
        call(SnapshotId='snap-1'), call(SnapshotId='snap-2')
    ]
    assert 'Unable to delete temporary snapshot snap-1' in caplog.text
    ec2.terminate_instances.assert_not_called()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_snapshots_after_instance_and_volumes(connect_mock):
    ec2 = MagicMock()
    ec2.describe_volumes.return_value = {
        'Volumes': [{'State': 'available', 'VolumeId': 'vol-1'}]
    }
    ec2.get_waiter().wait.return_value = None
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.instance_ids = ['i-donor']
    uploader.helper_instance = {'InstanceId': 'i-donor'}
    uploader.default_sleep = 0
    uploader.created_volumes = [{'VolumeId': 'vol-1'}]
    uploader.temporary_snapshot_ids = ['snap-1']

    uploader._clean_up()

    names = [c[0] for c in ec2.method_calls if c[0] in (
        'terminate_instances', 'delete_volume', 'delete_snapshot'
    )]
    assert names == [
        'terminate_instances', 'delete_volume', 'delete_snapshot'
    ]


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_launched_instance_without_helper_instance(connect_mock):
    ec2 = MagicMock()
    ec2.get_waiter().wait.return_value = None
    connect_mock.return_value = ec2
    uploader = _make_uploader()
    uploader.instance_ids = ['i-donor']
    uploader.default_sleep = 0

    uploader._clean_up()

    ec2.get_waiter().wait.assert_called_once_with(
        InstanceIds=['i-donor'],
        Filters=[{'Name': 'instance-state-name', 'Values': ['terminated']}]
    )


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_wait_status')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_volume_from_snapshot(
    connect_mock,
    show_progress_mock,
    check_wait_status_mock
):
    ec2 = MagicMock()
    ec2.create_volume.return_value = {'VolumeId': 'vol-1'}
    connect_mock.return_value = ec2
    check_wait_status_mock.return_value = 3

    uploader = _make_uploader()
    uploader.zone = 'myZone'
    volume = uploader._create_volume(12, 'snap-1')

    assert volume == {'VolumeId': 'vol-1'}
    ec2.create_volume.assert_called_once_with(
        Size=12,
        AvailabilityZone='myZone',
        VolumeType='gp2',
        SnapshotId='snap-1'
    )
    assert uploader.created_volumes == [{'VolumeId': 'vol-1'}]


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._set_zone_to_use')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_launch_helper_instance(
    connect_mock,
    set_zone_mock,
    show_progress_mock
):
    ec2 = MagicMock()
    ec2.run_instances.return_value = {
        'Instances': [{'InstanceId': 'myInstanceId'}]
    }
    ec2.get_waiter().wait.return_value = None
    connect_mock.return_value = ec2

    uploader = _root_swap_uploader(
        use_enclave=True, wait_count=1, vpc_subnet_id='subnet-1'
    )
    uploader.zone = 'myZone'
    with patch.object(uploader, '_check_wait_status', return_value=2):
        instance = uploader._launch_helper_instance()

    assert instance['InstanceId'] == 'myInstanceId'
    assert uploader.instance_ids == ['myInstanceId']
    assert ec2.run_instances.call_args[1] == {
        'ImageId': 'ami-donor',
        'MinCount': 1,
        'MaxCount': 1,
        'InstanceType': 't3.micro',
        'Placement': {'AvailabilityZone': 'myZone'},
        'EnclaveOptions': {'Enabled': True},
        'SubnetId': 'subnet-1',
        'TagSpecifications': [{
            'ResourceType': 'instance',
            'Tags': [{
                'Key': 'Name',
                'Value': 'ec2uploadimg-helper-instance'
            }]
        }]
    }


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._show_progress')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._set_zone_to_use')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_launch_helper_instance_without_ssh_arguments(
    connect_mock,
    set_zone_mock,
    show_progress_mock
):
    """No key pair, security group or public address is needed as the
       donor instance is never accessed"""
    ec2 = MagicMock()
    ec2.run_instances.return_value = {'Instances': [{'InstanceId': 'i-1'}]}
    connect_mock.return_value = ec2

    uploader = _make_uploader(
        launch_ami='ami-donor',
        vpc_subnet_id='',
        ssh_key_pair_name='key',
        security_group_ids='sg-1',
        use_private_ip=False
    )
    uploader.zone = 'myZone'
    with patch.object(uploader, '_check_wait_status', return_value=2):
        uploader._launch_helper_instance()

    launch_args = ec2.run_instances.call_args[1]
    for ignored in ('KeyName', 'NetworkInterfaces', 'SecurityGroupIds'):
        assert ignored not in launch_args
    assert 'SubnetId' not in launch_args


def test_launch_helper_instance_aborted():
    uploader = _root_swap_uploader()
    uploader.aborted = True
    assert uploader._launch_helper_instance() is None


@pytest.mark.parametrize('argument,value', [
    ('inst_user_name', 'root'),
    ('security_group_ids', 'sg-1'),
    ('ssh_key_pair_name', 'key'),
    ('ssh_key_private_key_file', '/key'),
    ('ssh_timeout', 10),
    ('channel_timeout', 10),
    ('use_private_ip', True)
])
def test_instantiation_ssh_arguments_deprecated(argument, value, caplog):
    uploader = _make_uploader(**{argument: value})
    assert 'deprecated and ignored' in caplog.text
    assert argument in caplog.text
    assert not hasattr(uploader, 'ssh_client')


def test_instantiation_default_ssh_arguments_no_warning(caplog):
    _make_uploader(ssh_timeout=300, channel_timeout=900, security_group_ids='')
    assert 'deprecated' not in caplog.text


def test_removed_ssh_code_is_gone():
    for name in (
        '_establish_ssh_connection', '_execute_ssh_command',
        '_end_ssh_session', '_upload_image', '_unpack_image',
        '_dump_root_fs', '_find_device_name', '_format_storage_volume',
        '_create_storage_volume', '_create_target_root_volume',
        '_check_security_groups_exist', '_get_next_disk_id'
    ):
        assert not hasattr(ec2upimg.EC2ImageUploader, name)
    assert not hasattr(ec2upimg, 'paramiko')


@patch('ec2imgutils.ec2uploadimg.time.sleep')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._set_zone_to_use')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_create_image_use_root_swap_complete_flow(
    connect_mock,
    check_image_exists_mock,
    set_zone_mock,
    sleep_mock,
    tmp_path
):
    """Run the complete root swap method with fake EBS and EC2 clients"""
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS()
    ec2 = MagicMock()
    ec2.get_waiter().wait.return_value = None
    ec2.run_instances.return_value = {
        'Instances': [{'InstanceId': 'i-donor'}]
    }
    ec2.create_volume.return_value = {'VolumeId': 'vol-new'}
    ec2.describe_volumes.side_effect = [
        {'Volumes': [{
            'VolumeId': 'vol-old',
            'State': 'in-use',
            'Attachments': [
                {'InstanceId': 'i-donor', 'Device': '/dev/sda1'}
            ]
        }]},
        {'Volumes': [{'VolumeId': 'vol-old', 'State': 'in-use'}]},
        {'Volumes': [{'VolumeId': 'vol-new', 'State': 'available'}]}
    ]
    ec2.describe_instances.return_value = {
        'Reservations': [{'Instances': [{
            'BlockDeviceMappings': [{
                'DeviceName': '/dev/sda1',
                'Ebs': {'DeleteOnTermination': True}
            }]
        }]}]
    }
    ec2.describe_images.return_value = {
        'Images': [{'VirtualizationType': 'hvm'}]
    }
    ec2.create_image.return_value = {'ImageId': 'ami-new'}
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )

    uploader = _make_uploader(
        launch_ami='ami-donor',
        upload_workers=2,
        image_tags=[{'Key': 'k', 'Value': 'v'}]
    )
    uploader.zone = 'zone-a'
    ami = uploader.create_image_use_root_swap(str(source))

    assert ami == 'ami-new'
    assert sorted(ebs.blocks) == [0, 2, 3]
    assert ebs.completed
    names = [c[0] for c in ec2.method_calls if c[0] in (
        'run_instances', 'create_volume', 'stop_instances', 'detach_volume',
        'attach_volume', 'create_image', 'terminate_instances',
        'delete_volume', 'delete_snapshot', 'create_tags'
    )]
    assert names == [
        'run_instances', 'create_volume', 'stop_instances', 'detach_volume',
        'attach_volume', 'create_image', 'terminate_instances',
        'delete_volume', 'delete_snapshot', 'create_tags'
    ]
    ec2.create_volume.assert_called_once_with(
        Size=10, AvailabilityZone='zone-a', VolumeType='gp2',
        SnapshotId='snap-1234'
    )
    ec2.attach_volume.assert_called_once_with(
        VolumeId='vol-new', InstanceId='i-donor', Device='/dev/sda1'
    )
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    assert ec2.create_image.call_args[1]['InstanceId'] == 'i-donor'


# -----------------------------------------------------------------------------
# Tests for guarding the instance given with running_id
def test_running_instance_not_cleaned_up_by_default():
    uploader = _make_uploader(running_id='i-running')
    assert uploader.instance_ids == []


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_clean_up_leaves_running_instance_alone(connect_mock):
    ec2 = MagicMock()
    connect_mock.return_value = ec2
    uploader = _make_uploader(running_id='i-running')

    uploader._clean_up()

    ec2.terminate_instances.assert_not_called()


def test_claim_running_instance():
    uploader = _make_uploader(running_id='i-running')
    uploader.instance_ids = ['i-other']
    uploader._claim_running_instance()
    uploader._claim_running_instance()
    assert uploader.instance_ids == ['i-other', 'i-running']


def test_claim_running_instance_launched_donor():
    uploader = _make_uploader()
    uploader.instance_ids = ['i-donor']
    uploader._claim_running_instance()
    assert uploader.instance_ids == ['i-donor']


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._wait_for_snapshot')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_image_exists')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_root_swap_failed_upload_keeps_running_instance(
    connect_mock,
    check_image_exists_mock,
    check_virt_type_mock,
    get_helper_mock,
    wait_for_snapshot_mock,
    tmp_path
):
    source = tmp_path / 'image.raw'
    _write_raw_image(source)
    ebs = FakeEBS(fail_on_put=0)
    ec2 = MagicMock()
    connect_mock.side_effect = (
        lambda service='ec2', config=None: ebs if service == 'ebs' else ec2
    )
    get_helper_mock.return_value = {'InstanceId': 'i-running'}

    uploader = _make_uploader(
        running_id='i-running', upload_workers=1, upload_retries=1
    )
    with pytest.raises(Exception):
        uploader.create_image_use_root_swap(str(source))

    # The pending snapshot is removed, the instance of the user is not
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1234')
    ec2.terminate_instances.assert_not_called()
    ec2.stop_instances.assert_not_called()
    ec2.create_volume.assert_not_called()


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._get_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_root_swap_failure_before_swap_keeps_running_instance(
    connect_mock,
    check_virt_type_mock,
    create_snapshot_mock,
    get_helper_mock,
    create_volume_mock
):
    ec2 = MagicMock()
    connect_mock.return_value = ec2
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    get_helper_mock.return_value = {'InstanceId': 'i-running'}
    create_volume_mock.side_effect = RuntimeError('create volume failed')

    uploader = _make_uploader(running_id='i-running')
    uploader.temporary_snapshot_ids = ['snap-1']
    with pytest.raises(RuntimeError):
        uploader.create_image_use_root_swap('source')

    ec2.terminate_instances.assert_not_called()
    ec2.stop_instances.assert_not_called()
    ec2.delete_snapshot.assert_called_once_with(SnapshotId='snap-1')


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._launch_helper_instance')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_snapshot_from_image')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_root_swap_failure_terminates_launched_donor(
    connect_mock,
    check_virt_type_mock,
    create_snapshot_mock,
    launch_mock,
    create_volume_mock
):
    ec2 = MagicMock()
    ec2.get_waiter().wait.return_value = None
    connect_mock.return_value = ec2
    create_snapshot_mock.return_value = {'SnapshotId': 'snap-1'}
    create_volume_mock.side_effect = RuntimeError('create volume failed')

    uploader = _make_uploader(launch_ami='ami-donor')
    uploader.default_sleep = 0

    def launch():
        uploader.instance_ids.append('i-donor')
        return {'InstanceId': 'i-donor'}

    launch_mock.side_effect = launch
    with pytest.raises(RuntimeError):
        uploader.create_image_use_root_swap('source')

    # An instance that was launched for the image is terminated
    ec2.terminate_instances.assert_called_once_with(InstanceIds=['i-donor'])


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._clean_up')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._create_image_root_volume')
@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._check_virt_type_consistent')
def test_root_swap_failed_clean_up_keeps_original_error(
    check_virt_type_mock,
    create_root_volume_mock,
    clean_up_mock,
    caplog
):
    create_root_volume_mock.side_effect = RuntimeError('original')
    clean_up_mock.side_effect = ValueError('clean up')

    uploader = _make_uploader()
    with pytest.raises(RuntimeError) as exc:
        uploader.create_image_use_root_swap('source')

    assert 'original' in str(exc.value)
    assert 'Clean up failed: clean up' in caplog.text


@patch('ec2imgutils.ec2uploadimg.EC2ImageUploader._connect')
def test_running_instance_terminated_after_swap_started(connect_mock):
    """Once the root volume of the instance is replaced it is part of the
       image creation and cleaned up with it"""
    ec2 = MagicMock()
    ec2.get_waiter().wait.return_value = None
    connect_mock.return_value = ec2
    uploader = _make_uploader(running_id='i-running')
    uploader.default_sleep = 0
    uploader.helper_instance = {'InstanceId': 'i-running'}

    uploader._claim_running_instance()
    uploader._clean_up()

    ec2.terminate_instances.assert_called_once_with(
        InstanceIds=['i-running']
    )


# -----------------------------------------------------------------------------
# Tests for the type check of the config of the client
@pytest.mark.parametrize('config,type_name', [
    ({'read_timeout': 5}, 'dict'),
    ('config', 'str'),
    (5, 'int')
])
@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_config_wrong_type(boto3_mock, config, type_name):
    uploader = _make_uploader(region='us-east-1')

    with pytest.raises(TypeError) as exc:
        uploader._connect(service='ebs', config=config)

    assert 'config must be a botocore.config.Config' in str(exc.value)
    assert type_name in str(exc.value)
    # Nothing is created before the check
    boto3_mock.client.assert_not_called()
    boto3_mock.session.Session.assert_not_called()


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_config_wrong_type_without_region(boto3_mock):
    uploader = _make_uploader()

    with pytest.raises(TypeError):
        uploader._connect(config={})

    assert uploader.region is None


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_config_accepted(boto3_mock):
    uploader = _make_uploader(region='us-east-1')
    config = botocore.config.Config(read_timeout=5)

    uploader._connect(service='ebs', config=config)

    session = boto3_mock.session.Session.return_value
    assert session.client.call_args[1]['config'] is config


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_config_accepted_session_token(boto3_mock):
    uploader = _make_uploader(region='us-east-1', session_token='token')
    config = botocore.config.Config(read_timeout=5)

    uploader._connect(service='ebs', config=config)

    assert boto3_mock.client.call_args[1]['config'] is config


@patch('ec2imgutils.ec2imgutils.boto3')
def test_connect_config_subclass_accepted(boto3_mock):

    class MyConfig(botocore.config.Config):
        pass

    uploader = _make_uploader(region='us-east-1')
    config = MyConfig()

    uploader._connect(config=config)

    session = boto3_mock.session.Session.return_value
    assert session.client.call_args[1]['config'] is config
