#!/usr/bin/python3
#
# Copyright (c) 2022 SUSE Linux GmbH.  All rights reserved.
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

import logging
import pytest
import os

from unittest.mock import patch, MagicMock

# Hack to get the script without the .py imported for testing
from importlib.machinery import SourceFileLoader

ec2uploadimg = SourceFileLoader(
    'ec2uploadimg',
    './ec2uploadimg'
).load_module()


# Global variables
this_path = os.path.dirname(os.path.abspath(__file__))
data_path = this_path + os.sep + 'data'

logger = logging.getLogger('ec2imgutils')
logger.setLevel(logging.DEBUG)


# --------------------------------------------------------------------
# Tests for valid parameters in parsing function
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--backing-store",
      "ssd",
      "--billing-codes",
      "testBillingCodes",
      "--boot-kernel",
      "testAkiID",
      "--boot-mode",
      "uefi",
      "--description",
      "This is a test description for the image",
      "--ec2-ami",
      "testAWSAmiId",
      "--ena-support",
      "--file",
      "/path/to/configuration/file",
      "--grub2",
      "--imds-support",
      "2.0",
      "--instance-id",
      "testInstanceId",
      "--machine",
      "x86_64",
      "--name",
      "testImageName",
      "--private-key-file",
      "testPrivateKeyFile",
      "--regions",
      "region1,region2,region3",
      "--root-volume-size",
      "33",
      "--ssh-key-pair",
      "testSshKeyPair",
      "--secret-key",
      "testAwsSecretKey",
      "--security-group-ids",
      "testSG1,testSG2",
      "--session-token",
      "testSessionToken",
      "--snaponly",
      "--sriov-support",
      "--ssh-timeout",
      "257",
      "--channel-timeout",
      "834",
      "--tpm-support",
      "2.0",
      "--type",
      "testType",
      "--user",
      "testUser",
      "--use-private-ip",
      "--use-root-swap",
      "--use-snapshot",
      "--virt-type",
      "testVirtType",
      "--verbose",
      "--vpc-subnet-id",
      "testVpcSubnetId",
      "--use-enclave",
      "--wait-count",
      "8",
      "testSource"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_args(cli_args):
    parsed_args = ec2uploadimg.parse_args(cli_args)
    assert parsed_args.accountName == "testAccName"
    assert parsed_args.accessKey == "testAccId"
    assert parsed_args.backingStore == "ssd"
    assert parsed_args.billingCodes == "testBillingCodes"
    assert parsed_args.akiID == "testAkiID"
    assert parsed_args.bootMode == "uefi"
    assert parsed_args.descript == "This is a test description for the image"
    assert parsed_args.amiID == "testAWSAmiId"
    assert parsed_args.ena is True
    assert parsed_args.configFilePath == "/path/to/configuration/file"
    assert parsed_args.grub2 is True
    assert parsed_args.runningID == "testInstanceId"
    assert parsed_args.arch == "x86_64"
    assert parsed_args.imgName == "testImageName"
    assert parsed_args.privateKey == "testPrivateKeyFile"
    assert parsed_args.regions == "region1,region2,region3"
    assert parsed_args.rootVolSize == "33"
    assert parsed_args.sshName == "testSshKeyPair"
    assert parsed_args.secretKey == "testAwsSecretKey"
    assert parsed_args.securityGroupIds == "testSG1,testSG2"
    assert parsed_args.sessionToken == "testSessionToken"
    assert parsed_args.snapOnly is True
    assert parsed_args.sriov is True
    assert parsed_args.sshTimeout == 257
    assert parsed_args.channelTimeout == 834
    assert parsed_args.tpm == "2.0"
    assert parsed_args.instType == "testType"
    assert parsed_args.sshUser == "testUser"
    assert parsed_args.usePrivateIP is True
    assert parsed_args.rootSwapMethod is True
    assert parsed_args.verbose == 1
    assert parsed_args.vpcSubnetId == "testVpcSubnetId"
    assert parsed_args.useEnclave is True
    assert parsed_args.waitCount == 8
    assert parsed_args.useSnap is True
    assert parsed_args.source == "testSource"
    assert parsed_args.imdsVersion == "2.0"


# --------------------------------------------------------------------
# Tests for valid parameters in check constraints
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--backing-store",
      "ssd",
      "--billing-codes",
      "testBillingCodes",
      "--boot-kernel",
      "testAkiID",
      "--boot-mode",
      "uefi",
      "--description",
      "This is a test description for the image",
      "--ec2-ami",
      "testAWSAmiId",
      "--ena-support",
      "--file",
      "/path/to/configuration/file",
      "--grub2",
      "--imds-support",
      "v2.0",
      "--machine",
      "x86_64",
      "--name",
      "testImageName",
      "--private-key-file",
      "testPrivateKeyFile",
      "--regions",
      "region1",
      "--root-volume-size",
      "33",
      "--ssh-key-pair",
      "testSshKeyPair",
      "--secret-key",
      "testAwsSecretKey",
      "--security-group-ids",
      "testSG1,testSG2",
      "--session-token",
      "testSessionToken",
      "--sriov-support",
      "--ssh-timeout",
      "257",
      "--channel-timeout",
      "834",
      "--tpm-support",
      "v2.0",
      "--type",
      "testType",
      "--user",
      "testUser",
      "--use-private-ip",
      "--use-snapshot",
      "--virt-type",
      "hvm",
      "--verbose",
      "--vpc-subnet-id",
      "testVpcSubnetId",
      "--use-enclave",
      "--wait-count",
      "8",
      "--image-tags",
      '[{"Key": "key", "Value": "value"}]',
      "testSource"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_args_check(cli_args):
    parsed_args = ec2uploadimg.parse_args(cli_args)
    ec2uploadimg.check_required_arguments_and_constraints(parsed_args, logger)
    assert parsed_args.accountName == "testAccName"
    assert parsed_args.accessKey == "testAccId"
    assert parsed_args.backingStore == "ssd"
    assert parsed_args.billingCodes == "testBillingCodes"
    assert parsed_args.akiID == "testAkiID"
    assert parsed_args.bootMode == "uefi"
    assert parsed_args.descript == "This is a test description for the image"
    assert parsed_args.amiID == "testAWSAmiId"
    assert parsed_args.ena is True
    assert parsed_args.configFilePath == "/path/to/configuration/file"
    assert parsed_args.grub2 is True
    assert parsed_args.arch == "x86_64"
    assert parsed_args.imgName == "testImageName"
    assert parsed_args.privateKey == "testPrivateKeyFile"
    assert parsed_args.regions == "region1"
    assert parsed_args.rootVolSize == "33"
    assert parsed_args.sshName == "testSshKeyPair"
    assert parsed_args.secretKey == "testAwsSecretKey"
    assert parsed_args.securityGroupIds == "testSG1,testSG2"
    assert parsed_args.sessionToken == "testSessionToken"
    assert parsed_args.snapOnly is False
    assert parsed_args.sriov is True
    assert parsed_args.sshTimeout == 257
    assert parsed_args.channelTimeout == 834
    assert parsed_args.tpm == "v2.0"
    assert parsed_args.instType == "testType"
    assert parsed_args.sshUser == "testUser"
    assert parsed_args.usePrivateIP is True
    assert parsed_args.rootSwapMethod is False
    assert parsed_args.verbose == 1
    assert parsed_args.useEnclave is True
    assert parsed_args.vpcSubnetId == "testVpcSubnetId"
    assert parsed_args.waitCount == 8
    assert parsed_args.source == "testSource"
    assert parsed_args.imdsVersion == "v2.0"
    assert str(parsed_args.imageTags) == "[{'Key': 'key', 'Value': 'value'}]"


# --------------------------------------------------------------------
# Tests for get_access_key functions
def test_check_snapshot_arguments():
    class Args:
        useSnap = True
        snapOnly = False
        rootSwapMethod = False

    myArgs = Args()
    ec2uploadimg.check_snapshot_arguments(myArgs, logger)


def test_check_snapshot_arguments_exception():

    class Args:
        useSnap = True
        snapOnly = True
        rootSwapMethod = False
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_snapshot_arguments(myArgs, logger)
    assert excinfo.value.code == 1


def test_check_snapshot_arguments_exception2():

    class Args:
        useSnap = True
        snapOnly = True
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_snapshot_arguments(myArgs, logger)
    assert excinfo.value.code == 1


def test_check_snapshot_arguments_exception3():

    class Args:
        useSnap = False
        snapOnly = False
        rootSwapMethod = False
        source = "/not/existing/file"
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_snapshot_arguments(myArgs, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_supported_arch_argument
def test_check_supported_arch_argument():

    class Args:
        arch = "NotSupportedArch"
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_supported_arch_argument(myArgs, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for all_arm64_images_to_support_ENA function
def test_all_arm64_images_to_support_ENA():

    class Args:
        arch = "arm64"
        ena = False
    myArgs = Args()
    ec2uploadimg.all_arm64_images_to_support_ENA(myArgs, logger)
    assert myArgs.ena is True


# --------------------------------------------------------------------
# Tests for check_tpm_support_has_allowed_boot_options function
def test_check_tpm_support_has_allowed_boot_options():

    class Args:
        tpm = '2.0'
        bootMode = "not_uefi"
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_tpm_support_has_allowed_boot_options(myArgs, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for config file management functions
test_cli_args_data = [
    (["--account",
      "testAccount",
      "-f",
      "/non/existing/file/path",
      "--description",
      "test description",
      "-m",
      "x86_64",
      "--name",
      "testName",
      "--regions",
      "region1,region2",
      "--use-snapshot",
      "testSource"], True),
]


@pytest.mark.parametrize(
    "cli_args,expected_exit",
    test_cli_args_data
)
def test_not_existing_config_file(cli_args, expected_exit):
    parsed_args = ec2uploadimg.parse_args(cli_args)
    if expected_exit:
        with pytest.raises(SystemExit) as excinfo:
            ec2uploadimg.get_config(parsed_args, logger)
        assert excinfo.value.code == 1


@pytest.mark.parametrize(
    "cli_args, expected_exit",
    test_cli_args_data
)
def test_get_invalid_config(cli_args, expected_exit):
    myArgs = ec2uploadimg.parse_args(cli_args)
    myArgs.configFilePath = data_path + os.sep + 'invalid.cfg'
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_config(myArgs, logger)
    assert excinfo.value.code == 1


def test_get_valid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2uploadimg.get_config(myArgs, logger)
    assert "AAAAAAAAAAAAAA" == str(
        config._sections["account-tester"]["access_key_id"]
    )


# --------------------------------------------------------------------
# Tests for get_access_key functions
def test_get_access_key():

    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    myArgs.accountName = 'tester'
    config = ec2uploadimg.get_config(myArgs, logger)
    access_key = ec2uploadimg.get_access_key(myArgs, config, logger)
    assert "AAAAAAAAAAAAAA" == access_key


def test_get_access_key_exception():

    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2uploadimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_access_key(myArgs, config, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_secret_key functions
def test_get_secret_key():

    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    myArgs.accountName = 'tester'
    config = ec2uploadimg.get_config(myArgs, logger)
    secret_key = ec2uploadimg.get_secret_key(myArgs, config, logger)
    assert "BBBBBBBBBBBBBBBBBBBBBBBB" == secret_key


def test_get_secret_key_exception():

    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2uploadimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_secret_key(myArgs, config, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_sriov_type
def test_get_sriov_type():

    class Args:
        sriov = True
    myArgs = Args()
    sriov_type = ec2uploadimg.get_sriov_type(myArgs)
    assert "simple" == sriov_type


# --------------------------------------------------------------------
# Tests for get_root_volume_size
def test_get_root_volume_size():

    class Args:
        rootVolSize = 22
    myArgs = Args()
    root_vol_size = ec2uploadimg.get_root_volume_size(myArgs)
    assert 22 == root_vol_size


def test_get_root_volume_size2():

    class Args:
        rootVolSize = 0
    myArgs = Args()
    root_vol_size = ec2uploadimg.get_root_volume_size(myArgs)
    assert 10 == root_vol_size


# --------------------------------------------------------------------
# Tests for get_uploader functions
@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader_exc1(EC2ImageUploader_mock, caplog):
    def my_side_eff(**kwargs):
        raise Exception('myException')

    EC2ImageUploader_mock.side_effect = my_side_eff

    myArgs = _parse()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_uploader(
            myArgs,
            "reg1",
            None,
            None,
            logger
        )
    assert excinfo.value.code == 1


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader_exc2(EC2ImageUploader_mock, caplog):
    def my_side_eff(**kwargs):
        raise ec2uploadimg.EC2UploadImgException

    EC2ImageUploader_mock.side_effect = my_side_eff

    myArgs = _parse()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_uploader(
            myArgs,
            "reg1",
            None,
            None,
            logger
        )
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for main
@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_main_happy_path_snapOnly(
    EC2ImageUploader_mock,
    caplog
):
    mySnapshot = {}
    mySnapshot['SnapshotId'] = 'mySnapshotId'
    ec2I = MagicMock()
    ec2I.create_snapshot.return_value = mySnapshot
    EC2ImageUploader_mock.return_value = ec2I

    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--private-key-file",
        data_path + os.sep + 'invalid.cfg',
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--security-group-ids",
        "testSG1,testSG2",
        "--snaponly",
        "--ssh-key-pair",
        "testSshKeyPair",
        "--type",
        "testType",
        "--user",
        "testUser",
        "--verbose",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    ec2uploadimg.main(cli_args)

    assert "Created snapshot" in caplog.text
    assert "mySnapshotId" in caplog.text


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_main_happy_path_useSnap(
    EC2ImageUploader_mock,
    caplog
):
    ec2I = MagicMock()
    ec2I.create_image_from_snapshot.return_value = 'myAmi'
    EC2ImageUploader_mock.return_value = ec2I

    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--private-key-file",
        data_path + os.sep + 'invalid.cfg',
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--security-group-ids",
        "testSG1,testSG2",
        "--ssh-key-pair",
        "testSshKeyPair",
        "--type",
        "testType",
        "--user",
        "testUser",
        "--use-snapshot",
        "--verbose",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    ec2uploadimg.main(cli_args)
    assert "Created image" in caplog.text
    assert "myAmi" in caplog.text


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_main_happy_path_other(
    EC2ImageUploader_mock,
    caplog
):
    ec2I = MagicMock()
    ec2I.create_image.return_value = 'myAmi'
    EC2ImageUploader_mock.return_value = ec2I

    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--private-key-file",
        data_path + os.sep + 'invalid.cfg',
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--security-group-ids",
        "testSG1,testSG2",
        "--ssh-key-pair",
        "testSshKeyPair",
        "--type",
        "testType",
        "--user",
        "testUser",
        "--verbose",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    ec2uploadimg.main(cli_args)
    assert "Created image" in caplog.text
    assert "myAmi" in caplog.text


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_failed_upload(
    EC2ImageUploader_mock,
    caplog
):
    ec2I = MagicMock()
    ec2I.create_image.return_value = 'myAmi'
    ec2I.create_image.side_effect = ValueError('upload failed (mock)')
    EC2ImageUploader_mock.return_value = ec2I

    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--security-group-ids",
        "testSG1,testSG2",
        "--ssh-key-pair",
        "testSshKeyPair",
        "--type",
        "testType",
        "--user",
        "testUser",
        "--verbose",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.main(cli_args)
    assert excinfo.value.code != 0


@patch('ec2uploadimg.utils.get_from_config')
def test_main_unable_to_get_access_keys(
    get_from_config_mock
):

    get_from_config_mock.return_value = None
    cli_args = [
        "--account",
        "testAccName",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--user",
        "testUser",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.main(cli_args)
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_main_unable_to_get_secret_keys(
    get_from_config_mock
):

    get_from_config_mock.return_value = None
    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--ec2-ami",
        "testAWSAmiId",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--regions",
        "region1",
        "--secret-key",
        "testAwsSecretKey",
        "--user",
        "testUser",
        "--use-root-swap",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.main(cli_args)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for the EBS direct upload (default) and root swap differences
def _parse(extra=None):
    cli_args = [
        "--description", "test description",
        "--machine", "x86_64",
        "--name", "testImageName",
        "--regions", "region1",
    ] + (extra or []) + [data_path + os.sep + 'complete.cfg']
    return ec2uploadimg.parse_args(cli_args)


def test_upload_workers_default():
    assert _parse().uploadWorkers == 8


def test_upload_workers_option():
    assert _parse(['--upload-workers', '4']).uploadWorkers == 4


def test_check_upload_workers():
    args = _parse(['--upload-workers', '1'])
    ec2uploadimg.check_upload_workers(args, logger)


@pytest.mark.parametrize('value', ['0', '-2'])
def test_check_upload_workers_invalid(value, caplog):
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_upload_workers(
            _parse(['--upload-workers', value]), logger
        )
    assert excinfo.value.code == 1
    assert 'upload workers' in caplog.text


# --------------------------------------------------------------------
# Tests for deprecated and removed options
def test_warn_deprecated_arguments(caplog):
    args = _parse([
        '--boot-kernel', 'aki-1',
        '--grub2',
        '--ec2-ami', 'ami-1',
        '--instance-id', 'i-1',
        '--ssh-key-pair', 'key',
        '--private-key-file', 'file',
        '--user', 'root',
        '--ssh-timeout', '10',
        '--channel-timeout', '10',
        '--security-group-ids', 'sg-1',
        '--vpc-subnet-id', 'subnet-1',
        '--use-private-ip',
        '--use-enclave',
        '--type', 't2.micro'
    ])

    ec2uploadimg.warn_deprecated_arguments(args, logger)

    assert 'deprecated and ignored' in caplog.text
    for _, option in ec2uploadimg.DEPRECATED_OPTIONS:
        assert option in caplog.text
    assert len(ec2uploadimg.DEPRECATED_OPTIONS) == 14


def test_warn_deprecated_arguments_none_given(caplog):
    ec2uploadimg.warn_deprecated_arguments(_parse(), logger)
    assert 'deprecated' not in caplog.text


def test_virt_type_hvm_accepted(caplog):
    args = _parse(['--virt-type', 'hvm'])
    ec2uploadimg.check_removed_arguments(args, logger)
    ec2uploadimg.warn_deprecated_arguments(args, logger)
    assert caplog.text == ''


def test_default_virt_type_accepted():
    ec2uploadimg.check_removed_arguments(_parse(), logger)


@pytest.mark.parametrize('value', ['para', 'paravirtual'])
def test_virt_type_para_rejected(value, caplog):
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_removed_arguments(
            _parse(['--virt-type', value]), logger
        )
    assert excinfo.value.code == 1
    assert 'Only hvm images are supported' in caplog.text


def test_root_swap_rejected(caplog):
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_removed_arguments(
            _parse(['--use-root-swap']), logger
        )
    assert excinfo.value.code == 1
    assert 'root swap method is no longer supported' in caplog.text


def test_removed_functions_are_gone():
    for name in (
        'get_bootkernel', 'get_virtualization_type', 'get_amiID',
        'get_ssh_user', 'get_vpc_subnet_id', 'get_security_group_ids',
        'get_inst_type', 'get_root_swap_arguments',
        'get_key_pair_name_and_ssh_private_key_file',
        'check_regions_parameter'
    ):
        assert not hasattr(ec2uploadimg, name)


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader(EC2ImageUploader_mock):
    args = _parse(['--upload-workers', '5', '--root-volume-size', '12'])

    uploader = ec2uploadimg.get_uploader(
        args, 'region1', 'access', 'secret', logger
    )

    assert uploader == EC2ImageUploader_mock.return_value
    kwargs = EC2ImageUploader_mock.call_args[1]
    assert kwargs['upload_workers'] == 5
    assert kwargs['root_volume_size'] == '12'
    assert kwargs['region'] == 'region1'
    assert kwargs['access_key'] == 'access'
    assert kwargs['secret_key'] == 'secret'
    for removed in (
        'bootkernel', 'image_virt_type', 'use_grub2', 'launch_ami',
        'running_id', 'inst_user_name', 'ssh_key_pair_name',
        'vpc_subnet_id', 'security_group_ids'
    ):
        assert removed not in kwargs


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_main_deprecated_options_do_not_need_config(
    EC2ImageUploader_mock,
    caplog
):
    ec2I = MagicMock()
    ec2I.create_image.return_value = 'myAmi'
    EC2ImageUploader_mock.return_value = ec2I

    ec2uploadimg.main([
        "--access-id", "testAccId",
        "--secret-key", "testAwsSecretKey",
        "--description", "test description",
        "--file", data_path + os.sep + 'complete.cfg',
        "--machine", "x86_64",
        "--name", "testImageName",
        "--regions", "region1,region2",
        "--ec2-ami", "ami-1",
        "--virt-type", "hvm",
        "--upload-workers", "2",
        data_path + os.sep + 'complete.cfg'
    ])

    assert 'Created image: myAmi' in caplog.text
    assert 'deprecated and ignored' in caplog.text
    assert EC2ImageUploader_mock.call_count == 2
    assert EC2ImageUploader_mock.call_args[1]['upload_workers'] == 2


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_main_aborted_upload_logs_nothing(EC2ImageUploader_mock, caplog):
    ec2I = MagicMock()
    ec2I.create_image.return_value = None
    EC2ImageUploader_mock.return_value = ec2I

    ec2uploadimg.main([
        "--access-id", "testAccId",
        "--secret-key", "testAwsSecretKey",
        "--description", "test description",
        "--file", data_path + os.sep + 'complete.cfg',
        "--machine", "x86_64",
        "--name", "testImageName",
        "--regions", "region1",
        data_path + os.sep + 'complete.cfg'
    ])

    assert 'Created image' not in caplog.text


# --------------------------------------------------------------------
# Tests for the upload retry and timeout options
def test_upload_retries_and_timeout_defaults():
    args = _parse()
    assert args.uploadWorkers == 8
    assert args.uploadRetries == 8
    assert args.uploadTimeout == 300


def test_upload_retries_and_timeout_options():
    args = _parse([
        '--upload-workers', '2',
        '--upload-retries', '12',
        '--upload-timeout', '600'
    ])
    assert args.uploadWorkers == 2
    assert args.uploadRetries == 12
    assert args.uploadTimeout == 600


def test_check_upload_retries_and_timeout_valid():
    args = _parse(['--upload-retries', '1', '--upload-timeout', '1'])
    ec2uploadimg.check_upload_retries(args, logger)
    ec2uploadimg.check_upload_timeout(args, logger)


@pytest.mark.parametrize('value', ['0', '-3'])
def test_check_upload_retries_invalid(value, caplog):
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_upload_retries(
            _parse(['--upload-retries', value]), logger
        )
    assert excinfo.value.code == 1
    assert 'upload retries' in caplog.text


@pytest.mark.parametrize('value', ['0', '-3'])
def test_check_upload_timeout_invalid(value, caplog):
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_upload_timeout(
            _parse(['--upload-timeout', value]), logger
        )
    assert excinfo.value.code == 1
    assert 'upload timeout' in caplog.text


def test_checks_reject_invalid_retries_and_timeout():
    for option in ('--upload-retries', '--upload-timeout'):
        args = _parse([option, '0'])
        args.source = data_path + os.sep + 'complete.cfg'
        with pytest.raises(SystemExit):
            ec2uploadimg.check_required_arguments_and_constraints(
                args, logger
            )


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader_passes_retries_and_timeout(EC2ImageUploader_mock):
    args = _parse([
        '--upload-workers', '3',
        '--upload-retries', '5',
        '--upload-timeout', '120'
    ])

    ec2uploadimg.get_uploader(args, 'cn-north-1', 'access', 'secret', logger)

    kwargs = EC2ImageUploader_mock.call_args[1]
    assert kwargs['upload_workers'] == 3
    assert kwargs['upload_retries'] == 5
    assert kwargs['upload_timeout'] == 120
