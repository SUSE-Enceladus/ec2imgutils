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
logger.setLevel(logging.INFO)


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
      "--type",
      "testType",
      "--user",
      "testUser",
      "--use-private-ip",
      "--use-root-swap",
      "--virt-type",
      "testVirtType",
      "--verbose",
      "--vpc-subnet-id",
      "testVpcSubnetId",
      "--wait-count",
      "8",
      "--use-snapshot",
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
