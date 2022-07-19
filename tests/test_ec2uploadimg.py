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
    assert parsed_args.tpm == "2.0"
    assert parsed_args.instType == "testType"
    assert parsed_args.sshUser == "testUser"
    assert parsed_args.usePrivateIP is True
    assert parsed_args.rootSwapMethod is True
    assert parsed_args.verbose == 1
    assert parsed_args.vpcSubnetId == "testVpcSubnetId"
    assert parsed_args.waitCount == 8
    assert parsed_args.useSnap is True
    assert parsed_args.source == "testSource"


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
      "--tpm-support",
      "2.0",
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
      "--wait-count",
      "8",
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
    assert parsed_args.tpm == "2.0"
    assert parsed_args.instType == "testType"
    assert parsed_args.sshUser == "testUser"
    assert parsed_args.usePrivateIP is True
    assert parsed_args.rootSwapMethod is False
    assert parsed_args.verbose == 1
    assert parsed_args.vpcSubnetId == "testVpcSubnetId"
    assert parsed_args.waitCount == 8
    assert parsed_args.source == "testSource"


# --------------------------------------------------------------------
# Tests for get_access_key functions
def test_check_snapshot_arguments():
    global logger

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
        snapOnly = False
        rootSwapMethod = True
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
# Tests for check_sriov_image_is_hvm function
def test_check_sriov_image_is_hvm():

    class Args:
        sriov = True
        virtType = "not_hvm"
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_sriov_image_is_hvm(myArgs, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for check_amiID_or_runningID_provided function
def test_check_amiID_or_runningID_provided():

    class Args:
        amiID = 'testAmiID'
        runningID = "testRunningID"
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_amiID_or_runningID_provided(myArgs, logger)
    assert excinfo.value.code == 1


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
# Tests for check_regions_parameter function
def test_check_regions_parameter():

    class Args:
        regions = 'region1,region2,region3'
        amiID = 'testAmiID'
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_regions_parameter(myArgs, logger)
    assert excinfo.value.code == 1


def test_check_regions_parameter2():

    class Args:
        regions = 'region1,region2,region3'
        amiID = ''
        akiID = 'testAkiID'
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_regions_parameter(myArgs, logger)
    assert excinfo.value.code == 1


def test_check_regions_parameter3():

    class Args:
        regions = 'region1,region2,region3'
        amiID = ''
        akiID = ''
        runningID = 'testRunningID'
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_regions_parameter(myArgs, logger)
    assert excinfo.value.code == 1


def test_check_regions_parameter4():

    class Args:
        regions = 'region1,region2,region3'
        amiID = ''
        akiID = ''
        runningID = ''
        vpcSubnetId = 'testVpcSubnetId'
    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_regions_parameter(myArgs, logger)
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
# Tests for get_virtualization_type
def test_get_virtualization_type():

    class Args:
        virtType = 'para'
    myArgs = Args()
    virt_type = ec2uploadimg.get_virtualization_type(myArgs)
    assert "paravirtual" == virt_type


def test_get_virtualization_type2():

    class Args:
        virtType = 'not_para'
    myArgs = Args()
    virt_type = ec2uploadimg.get_virtualization_type(myArgs)
    assert "not_para" == virt_type


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
# Tests for get_access_key functions
def test_check_ena_image_is_hvm():
    global logger

    class Args:
        ena = True
        virtType = "notHVM"

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.check_ena_image_is_hvm(myArgs, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_bootkernel functions
def test_get_bootkernel_hvm():
    global logger

    class Args:
        akiID = "testBootkernel"
        virtType = "hvm"

    myArgs = Args()
    bk = ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert bk is None


@patch('ec2uploadimg.utils.get_from_config')
def test_get_bootkernel_grub2(get_from_config_mock):
    get_from_config_mock.return_value = "myBootKernel"
    global logger

    class Args:
        accountName = 'testAccountName'
        akiID = None
        virtType = "nothvm"
        grub2 = True

    myArgs = Args()
    bk = ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert bk == "myBootKernel"


@patch('ec2uploadimg.utils.get_from_config')
def test_get_bootkernel_arch_x86_64(get_from_config_mock):
    get_from_config_mock.return_value = "myBootKernel"
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'x86_64'
        akiID = None
        virtType = "nothvm"
        grub2 = False

    myArgs = Args()
    bk = ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert bk == "myBootKernel"


@patch('ec2uploadimg.utils.get_from_config')
def test_get_bootkernel_arch_i386(get_from_config_mock):
    get_from_config_mock.return_value = "myBootKernel"
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'i386'
        akiID = None
        virtType = "nothvm"
        grub2 = False

    myArgs = Args()
    bk = ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert bk == "myBootKernel"


def test_get_bootkernel_arch_arm64():
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'arm64'
        akiID = None
        virtType = "nothvm"
        grub2 = False

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert excinfo.value.code == 1


def test_get_bootkernel_arch_other():
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'other'
        akiID = None
        virtType = "nothvm"
        grub2 = False

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert excinfo.value.code == 1


def test_get_bootkernel_exc():
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'i386'
        akiID = None
        virtType = "nothvm"
        grub2 = False

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_bootkernel(myArgs, None, "region1", logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_amiID
@patch('ec2uploadimg.utils.get_from_config')
def test_get_amiID(get_from_config_mock):
    get_from_config_mock.return_value = "myAmiID"
    global logger

    class Args:
        accountName = 'testAccountName'
        arch = 'x86_64'
        akiID = None

    myArgs = Args()
    amiID = ec2uploadimg.get_amiID(myArgs, None, "region1", logger)
    assert amiID == "myAmiID"


# --------------------------------------------------------------------
# Tests for get_ssh_user functions
def test_get_ssh_user():
    global logger

    class Args:
        accountName = 'testAccountName'
        sshUser = 'mySshUser'

    myArgs = Args()
    sshUser = ec2uploadimg.get_ssh_user(myArgs, None, "reg1", logger)
    assert sshUser == 'mySshUser'


@patch('ec2uploadimg.utils.get_from_config')
def test_get_ssh_user_config(get_from_config_mock):
    global logger

    get_from_config_mock.return_value = 'mySshUser'

    class Args:
        accountName = 'testAccountName'
        sshUser = None

    myArgs = Args()
    sshUser = ec2uploadimg.get_ssh_user(myArgs, None, "reg1", logger)
    assert sshUser == 'mySshUser'


@patch('ec2uploadimg.utils.get_from_config')
def test_get_ssh_user_config_exc(get_from_config_mock, caplog):
    global logger

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    class Args:
        accountName = 'testAccountName'
        sshUser = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_ssh_user(myArgs, None, "reg1", logger)
    assert 'myexception' in caplog.text
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_get_ssh_user_config_exc2(get_from_config_mock, caplog):
    global logger

    get_from_config_mock.return_value = None

    class Args:
        accountName = 'testAccountName'
        sshUser = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_ssh_user(myArgs, None, "reg1", logger)
    assert 'Could not determine ssh user to use' in caplog.text
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_key_pair_name_and_ssh_private_key_file function
def test_get_key_pair_name_and_ssh_private_key_file_file_not_exists(caplog):

    global logger
    setup = MagicMock()
    setup.create_upload_key_pair.return_value = \
        ('myKeyPairName', 'myPrivateKeyFile')

    class Args:
        accountName = None
        sshName = None
        privateKey = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_key_pair_name_and_ssh_private_key_file(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'SSH private key file' in caplog.text
    assert 'does not exist' in caplog.text
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_get_key_pair_name_and_ssh_private_key_file_file_nopairname(
    get_from_config_mock,
    caplog
):

    global logger
    setup = MagicMock()
    setup.create_upload_key_pair.return_value = \
        (None, None)

    get_from_config_mock.return_value = None

    class Args:
        accountName = None
        sshName = None
        privateKey = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_key_pair_name_and_ssh_private_key_file(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'Could not determine key pair name' in caplog.text
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_get_key_pair_name_and_ssh_private_key_file_file_exc(
    get_from_config_mock,
    caplog
):

    global logger
    setup = MagicMock()
    setup.create_upload_key_pair.return_value = \
        (None, None)

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    class Args:
        accountName = None
        sshName = None
        privateKey = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_key_pair_name_and_ssh_private_key_file(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'myexception' in caplog.text
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_get_key_pair_name_and_ssh_private_key_file_nokeyfile(
    get_from_config_mock,
    caplog
):

    global logger
    setup = MagicMock()
    setup.create_upload_key_pair.return_value = \
        ('keyPairName', None)

    get_from_config_mock.return_value = None

    class Args:
        accountName = None
        sshName = None
        privateKey = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_key_pair_name_and_ssh_private_key_file(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'SSH private key file' in caplog.text
    assert 'does not exist' in caplog.text
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_get_key_pair_name_and_ssh_private_key_file_exc(
    get_from_config_mock,
    caplog
):

    global logger
    setup = MagicMock()
    setup.create_upload_key_pair.return_value = \
        ('keyPairName', None)

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    class Args:
        accountName = 'ec2-user'
        sshName = 'mySshName'
        privateKey = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_key_pair_name_and_ssh_private_key_file(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'myexception' in caplog.text
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_vpc_subnet_id functions
def test_get_vpc_subnet_id(caplog):
    global logger

    logger.setLevel(logging.DEBUG)
    setup = MagicMock()
    setup.create_vpc_subnet.return_value = 'vpcSubnetId'

    class Args:
        accountName = None
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    vpc_subnet_id = ec2uploadimg.get_vpc_subnet_id(
        myArgs,
        None,
        "reg1",
        setup,
        logger
    )
    assert 'Using VPC subnet: vpcSubnetId' in caplog.text
    assert 'vpcSubnetId' == vpc_subnet_id
    logger.setLevel(logging.INFO)


@patch('ec2uploadimg.utils.get_from_config')
def test_get_vpc_subnet_id_exc(get_from_config_mock, caplog):
    global logger

    setup = MagicMock()

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    class Args:
        accountName = 'testAccountName'
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_vpc_subnet_id(
            myArgs,
            None,
            "reg1",
            setup,
            logger
        )
    assert 'Not using a subnet-id, none given on the' in caplog.text
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_vpc_subnet_id functions
def test_get_security_group_ids(caplog):
    global logger

    setup = MagicMock()
    setup.create_security_group.return_value = 'securityGroupId'

    class Args:
        accountName = None
        securityGroupIds = None
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    sec_group_ids = ec2uploadimg.get_security_group_ids(
        myArgs,
        None,
        "reg1",
        None,
        None,
        setup,
        None,
        logger
    )
    assert 'securityGroupId' == sec_group_ids


@patch('ec2uploadimg.utils.get_from_config')
def test_get_security_group_ids_accName(get_from_config_mock, caplog):
    global logger

    # setup = MagicMock()
    # setup.create_security_group.return_value = 'securityGroupId'
    logger.setLevel(logging.DEBUG)
    get_from_config_mock.return_value = 'securityGroupId'

    class Args:
        accountName = "testAccName"
        securityGroupIds = None
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    sec_group_ids = ec2uploadimg.get_security_group_ids(
        myArgs,
        None,
        "reg1",
        None,
        None,
        None,
        None,
        logger
    )
    assert 'Using Security Group IDs: securityGroupId' in caplog.text
    assert 'securityGroupId' == sec_group_ids


@patch('ec2uploadimg.boto3.client')
@patch('ec2uploadimg.utils.get_from_config')
def test_get_security_group_ids_accName_exc(
    get_from_config_mock,
    boto3_client_mock,
    caplog
):
    global logger

    # setup = MagicMock()
    # setup.create_security_group.return_value = 'securityGroupId'
    logger.setLevel(logging.DEBUG)

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    ec2 = MagicMock()
    subnet = {}
    subnet['VpcId'] = 'myVpcId'
    subnets = []
    subnets.append(subnet)
    mySubnets = {}
    mySubnets['Subnets'] = subnets
    ec2.describe_subnets.return_value = mySubnets

    boto3_client_mock.return_value = ec2

    setup = MagicMock()
    setup.create_security_group.return_value = 'mySecurityGroupId'

    class Args:
        accountName = "testAccName"
        securityGroupIds = None
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    sec_group_ids = ec2uploadimg.get_security_group_ids(
        myArgs,
        None,
        "reg1",
        None,
        None,
        setup,
        'vpdSubnetId',
        logger
    )
    assert 'No security group specified in the config' in caplog.text
    assert sec_group_ids == 'mySecurityGroupId'


@patch('ec2uploadimg.boto3.client')
@patch('ec2uploadimg.utils.get_from_config')
def test_get_security_group_ids_accName_exc_noSubnets(
    get_from_config_mock,
    boto3_client_mock,
    caplog
):
    global logger

    # setup = MagicMock()
    # setup.create_security_group.return_value = 'securityGroupId'
    logger.setLevel(logging.DEBUG)

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myexception')

    get_from_config_mock.side_effect = my_side_eff

    ec2 = MagicMock()
    # subnet = {}
    #  subnet['VpcId'] = 'myVpcId'
    subnets = []
    # subnets.append(subnet)
    mySubnets = {}
    mySubnets['Subnets'] = subnets
    ec2.describe_subnets.return_value = mySubnets

    boto3_client_mock.return_value = ec2

    setup = MagicMock()
    setup.create_security_group.return_value = 'mySecurityGroupId'

    class Args:
        accountName = "testAccName"
        securityGroupIds = None
        vpcSubnetId = None
        amiID = None
        runningID = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_security_group_ids(
            myArgs,
            None,
            "reg1",
            None,
            None,
            setup,
            'vpdSubnetId',
            logger
        )
    assert 'No security group specified in the config' in caplog.text
    assert 'Unable to obtain VPC information for' in caplog.text
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_inst_type functions
@patch('ec2uploadimg.utils.get_from_config')
def test_get_inst_type_exc(get_from_config_mock, caplog):
    global logger

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myException')

    get_from_config_mock.side_effect = my_side_eff

    class Args:
        accountName = 'myAccountName'
        instType = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_inst_type(
            myArgs,
            None,
            "reg1",
            logger
        )
    assert 'Could not find instance_type' in caplog.text
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for get_uploader functions
@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader_exc1(EC2ImageUploader_mock, caplog):
    global logger

    def my_side_eff(a1, a2, a3, a4, a5):
        raise Exception('myException')

    EC2ImageUploader_mock.side_effect = my_side_eff

    class Args:
        accountName = None
        amiID = None
        runningID = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_uploader(
            myArgs,
            "reg1",
            None,
            None,
            None,
            None,
            logger
        )
    assert excinfo.value.code == 1


@patch('ec2uploadimg.ec2upimg.EC2ImageUploader')
def test_get_uploader_exc2(EC2ImageUploader_mock, caplog):
    global logger

    def my_side_eff(a1, a2, a3, a4, a5):
        raise ec2uploadimg.EC2UploadImgException

    EC2ImageUploader_mock.side_effect = my_side_eff

    class Args:
        accountName = None
        amiID = None
        runningID = None

    myArgs = Args()
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.get_uploader(
            myArgs,
            "reg1",
            None,
            None,
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
def test_main_happy_path_rootSwapMethod(
    EC2ImageUploader_mock,
    caplog
):
    ec2I = MagicMock()
    ec2I.create_image_use_root_swap.return_value = 'myAmi'
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
        "--use-root-swap",
        "--verbose",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    ec2uploadimg.main(cli_args)
    assert "Created image" in caplog.text
    assert "myAmi" in caplog.text


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
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.main(cli_args)
    assert excinfo.value.code == 1


@patch('ec2uploadimg.utils.get_from_config')
def test_main_unable_to_get_amiID(
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
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--regions",
        "region1",
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
def test_main_unable_to_get_bootkernel_hvm(
    get_from_config_mock
):

    get_from_config_mock.side_effect = ["testAmiID"]
    cli_args = [
        "--account",
        "testAccName",
        "--access-id",
        "testAccId",
        "--description",
        "This is a test description for the image",
        "--file",
        data_path + os.sep + 'complete.cfg',
        "--machine",
        "x86_64",
        "--name",
        "testImageName",
        "--regions",
        "region1",
        "--user",
        "testUser",
        "--virt-type",
        "hvm",
        data_path + os.sep + 'complete.cfg'
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2uploadimg.main(cli_args)
    assert excinfo.value.code == 1
