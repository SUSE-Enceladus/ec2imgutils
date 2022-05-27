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
import argparse

from unittest.mock import patch, MagicMock

# Hack to get the script without the .py imported for testing
from importlib.machinery import SourceFileLoader

ec2deprecateimg = SourceFileLoader(
    'ec2deprecateimg',
    './ec2deprecateimg'
).load_module()


# Global variables
this_path = os.path.dirname(os.path.abspath(__file__))
data_path = this_path + os.sep + 'data'

logger = logging.getLogger('ec2imgutils')
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------
# Tests for valid_YYYYMMDD_date function
test_depr_date_data = [
    ("asdf", True),
    ("20202001", True),
    ("20200230", True),
    ("20200130", False),
    ("20220202", False),
]


@pytest.mark.parametrize(
    "depr_date,expected_exc",
    test_depr_date_data
)
def test_valid_YYYYMMDD_date(depr_date, expected_exc):
    """Test valid_YYYYMMDD_date function"""
    if expected_exc:
        with pytest.raises(argparse.ArgumentTypeError) as depr_exc:
            ec2deprecateimg.valid_YYYYMMDD_date(depr_date)
        assert depr_date in str(depr_exc.value)
        assert 'not a valid date' in str(depr_exc.value)
    else:
        returned_depr_date = ec2deprecateimg.valid_YYYYMMDD_date(depr_date)

        assert depr_date == returned_depr_date


# --------------------------------------------------------------------
# Tests for valid parameters in parsing function
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "6",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--force",
      "--image-name",
      "testImageName",
      "--image-virt-type",
      "hvm",
      "--public-only",
      "--replacement-name",
      "testReplacementName",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_args(cli_args):
    parsed_args = ec2deprecateimg.parse_args(cli_args)
    ec2deprecateimg.check_required_arguments(parsed_args, logger)
    assert parsed_args.accountName == "testAccName"
    assert parsed_args.accessKey == "testAccId"
    assert parsed_args.depDate == "20220101"
    assert parsed_args.depTime == 6
    assert parsed_args.dryRun is True
    assert parsed_args.configFilePath == "/path/to/configuration/file"
    assert parsed_args.force is True
    assert parsed_args.depImgName == "testImageName"
    assert parsed_args.virtType == "hvm"
    assert parsed_args.publicOnly is True
    assert parsed_args.replImgName == "testReplacementName"
    assert parsed_args.regions == "region1,region2,region3"
    assert parsed_args.secretKey == "testSecretKey"
    assert parsed_args.verbose is True


# --------------------------------------------------------------------
# Tests for required parameters not present
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "-n",
      "--force"], True)
]


@pytest.mark.parametrize(
    "cli_args,expected_exit",
    test_cli_args_data
)
def test_required_image_args_not_present(cli_args, expected_exit):
    if expected_exit:
        with pytest.raises(SystemExit) as excinfo:
            parsed_args = ec2deprecateimg.parse_args(cli_args)
            ec2deprecateimg.check_required_arguments(parsed_args, logger)
        assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for arguments exclusive group
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--force",
      "--image-name",
      "testImageName",
      "--image-id",
      "testImageAMIid",
      "--replacement-name",
      "testReplacementName",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_image_arguments_exclusive_group(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        parsed_args = ec2deprecateimg.parse_args(cli_args)
        ec2deprecateimg.check_required_arguments(parsed_args, logger)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for wrong format in deprecation-date
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "2022/01/01",
      "--image-name",
      "testImageName",
      "--replacement-name",
      "testReplacementName",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_wrong_format_deprecation_date_parameter(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.parse_args(cli_args)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for wrong format in deprecation-period
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-period",
      "six",
      "--image-name",
      "testImageName",
      "--replacement-name",
      "testReplacementName",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_wrong_format_deprecation_period_parameter(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.parse_args(cli_args)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for wrong virtualization-type
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--image-virt-type",
      "not_supported_value",
      "--image-name",
      "testImageName",
      "--replacement-name",
      "testReplacementName",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_wrong_virtualization_type(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.parse_args(cli_args)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for config file management functions
test_cli_args_data = [
    (["--account",
      "testAccount",
      "--image-name",
      "testImageName",
      "--replacement-name",
      "testReplacementName",
      "-n",
      "-f",
      "/non/existing/file/path"], True),
]


@pytest.mark.parametrize(
    "cli_args,expected_exit",
    test_cli_args_data
)
def test_not_existing_config_file(cli_args, expected_exit):
    parsed_args = ec2deprecateimg.parse_args(cli_args)
    if expected_exit:
        with pytest.raises(SystemExit) as excinfo:
            ec2deprecateimg.get_config(parsed_args, logger)
        assert excinfo.value.code == 1


def test_get_invalid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'invalid.cfg'
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.get_config(myArgs, logger)
    assert excinfo.value.code == 1


def test_get_valid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2deprecateimg.get_config(myArgs, logger)
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
    config = ec2deprecateimg.get_config(myArgs, logger)
    access_key = ec2deprecateimg.get_access_key(myArgs, config, logger)
    assert "AAAAAAAAAAAAAA" == access_key


def test_get_access_key_exception():
    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2deprecateimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.get_access_key(myArgs, config, logger)
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
    config = ec2deprecateimg.get_config(myArgs, logger)
    secret_key = ec2deprecateimg.get_secret_key(myArgs, config, logger)
    assert "BBBBBBBBBBBBBBBBBBBBBBBB" == secret_key


def test_get_secret_key_exception():
    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2deprecateimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.get_secret_key(myArgs, config, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for deprecator class initialization

test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "6",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--force",
      "--image-name",
      "testImageName",
      "--image-virt-type",
      "hvm",
      "--public-only",
      "--replacement-name",
      "testReplacementName",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_deprecator_init(cli_args):
    parsed_args = ec2deprecateimg.parse_args(cli_args)
    deprecator = ec2deprecateimg.get_image_deprecator(
        parsed_args,
        parsed_args.accessKey,
        parsed_args.secretKey,
        logger
    )
    assert deprecator.access_key == "testAccId"
    assert deprecator.secret_key == "testSecretKey"


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_deprecator_init_exception(cli_args):
    parsed_args = ec2deprecateimg.parse_args(cli_args)
    parsed_args.depDate = '123'
    with pytest.raises(SystemExit) as excinfo:
        ec2deprecateimg.get_image_deprecator(
            parsed_args,
            parsed_args.accessKey,
            parsed_args.secretKey,
            logger
        )
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for main function
@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._get_owned_images')
@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._connect')
def test_deprecate_images_filtering_by_name(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))


    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "7",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "testImageName",
      "--image-virt-type",
      "hvm",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2deprecateimg.main(cli_args)
    assert "20220101" in caplog.text
    assert "20220801" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text


@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._get_owned_images')
@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._connect')
def test_deprecate_images_filtering_by_id(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))


    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "7",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--image-virt-type",
      "hvm",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2deprecateimg.main(cli_args)
    assert "20220101" in caplog.text
    assert "20220801" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text


@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._get_owned_images')
@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._connect')
def test_deprecate_images_filtering_by_name_match(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))


    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "7",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*Name$",
      "--image-virt-type",
      "hvm",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2deprecateimg.main(cli_args)
    assert "20220101" in caplog.text
    assert "20220801" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text


@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._get_owned_images')
@patch('ec2deprecateimg.ec2depimg.EC2DeprecateImg._connect')
def test_deprecate_images_filtering_by_name_match_dry_run(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))


    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--deprecation-date",
      "20220101",
      "--deprecation-period",
      "7",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*Name$",
      "--dry-run",
      "--image-virt-type",
      "hvm",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2deprecateimg.main(cli_args)
    assert "20220101" in caplog.text
    assert "20220801" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text





# --------------------------------------------------------------------
# Aux functions
def mock_get_owned_images():
    myImage1 = {}
    myImage1["Architecture"] = "x86_64"
    myImage1["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage1["ImageId"] = "ami-000cc31892067693a"
    myImage1["Name"] = "testImageName"
    myI1Ebs = {}
    myI1Ebs["DeleteOnTermination"] = True
    myI1Ebs["SnapshotId"] = "snap-000f48a8fa4545e1a"
    myI1Ebs["VolumeSize"] = 10
    myI1Ebs["VolumeType"] = "gp3"
    myI1Ebs["Encrypted"] = False
    bdmI1 = {}
    bdmI1["DeviceName"] = "/dev/sda1"
    bdmI1["Ebs"] = myI1Ebs
    myImage1["BlockDeviceMappings"] = []
    myImage1["BlockDeviceMappings"].append(bdmI1)
    myImage1["VirtualizationType"] = "hvm"

    myImage2 = {}
    myImage2["Architecture"] = "x86_64"
    myImage2["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage2["ImageId"] = "ami-000cc31892067693b"
    myImage2["Name"] = "NotTestImage"
    myI2Ebs = {}
    myI2Ebs["DeleteOnTermination"] = True
    myI2Ebs["SnapshotId"] = "snap-000f48a8fa4545e1b"
    myI2Ebs["VolumeSize"] = 10
    myI2Ebs["VolumeType"] = "gp3"
    myI2Ebs["Encrypted"] = False
    bdmI2 = {}
    bdmI2["DeviceName"] = "/dev/sda1"
    bdmI2["Ebs"] = myI2Ebs
    myImage2["BlockDeviceMappings"] = []
    myImage2["BlockDeviceMappings"].append(bdmI2)
    myImage2["VirtualizationType"] = "hvm"
    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    return myImages

