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
    config = object()

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


def test_determine_root_device():
    assert _make_uploader()._determine_root_device() == '/dev/sda1'


def test_removed_constructor_arguments():
    for argument in (
        'bootkernel', 'image_virt_type', 'launch_ami', 'running_id',
        'ssh_key_pair_name', 'use_grub2', 'vpc_subnet_id'
    ):
        with pytest.raises(TypeError):
            _make_uploader(**{argument: 'value'})


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
