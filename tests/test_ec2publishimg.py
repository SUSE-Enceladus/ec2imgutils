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

ec2publishimg = SourceFileLoader(
    'ec2publishimg',
    './ec2publishimg'
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
      "--allow-copy",
      "none",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "all",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_args(cli_args):
    parsed_args = ec2publishimg.parse_args(cli_args)
    assert parsed_args.accountName == "testAccName"
    assert parsed_args.accessKey == "testAccId"
    assert parsed_args.allowCopy == "none"
    assert parsed_args.dryRun is True
    assert parsed_args.configFilePath == "/path/to/configuration/file"
    assert parsed_args.pubImgName == "testImageName"
    assert parsed_args.regions == "region1,region2,region3"
    assert parsed_args.secretKey == "testSecretKey"
    assert parsed_args.share == "all"
    assert parsed_args.verbose is True


# --------------------------------------------------------------------
# Tests for arguments exclusive group
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--image-id",
      "testImageAMIid",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "all",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_image_arguments_exclusive_group(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.parse_args(cli_args)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for mandatory arguments provided
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "all",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_image_arguments_absent(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        parsed_args = ec2publishimg.parse_args(cli_args)
        ec2publishimg.check_required_arguments(parsed_args, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for allow-copy argument
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "not_valid_value",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "all",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_allow_copy_arguments(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        parsed_args = ec2publishimg.parse_args(cli_args)
        ec2publishimg.check_required_arguments(parsed_args, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for share argument
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--regions",
      "region1,region2,region3",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "not_valid_value",
      "--verbose"]),
]


@pytest.mark.parametrize(
    "cli_args",
    test_cli_args_data
)
def test_share_arguments(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        parsed_args = ec2publishimg.parse_args(cli_args)
        ec2publishimg.check_required_arguments(parsed_args, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for config file management functions
test_cli_args_data = [
    (["--account",
      "testAccount",
      "-f",
      "/non/existing/file/path"], True),
]


@pytest.mark.parametrize(
    "cli_args,expected_exit",
    test_cli_args_data
)
def test_not_existing_config_file(cli_args, expected_exit):
    parsed_args = ec2publishimg.parse_args(cli_args)
    if expected_exit:
        with pytest.raises(SystemExit) as excinfo:
            ec2publishimg.get_config(parsed_args, logger)
        assert excinfo.value.code == 1


def test_get_invalid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'invalid.cfg'
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.get_config(myArgs, logger)
    assert excinfo.value.code == 1


def test_get_valid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2publishimg.get_config(myArgs, logger)
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
    config = ec2publishimg.get_config(myArgs, logger)
    access_key = ec2publishimg.get_access_key(myArgs, config, logger)
    assert "AAAAAAAAAAAAAA" == access_key


@patch('ec2publishimg.utils.get_from_config')
def test_get_access_key_none(get_from_config_mock, caplog):
    get_from_config_mock.return_value = None

    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    myArgs.accountName = 'tester'
    config = ec2publishimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.get_access_key(myArgs, config, logger)
    assert excinfo.value.code == 1
    assert 'Could not determine account access key' in caplog.text


def test_get_access_key_exception():
    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2publishimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.get_access_key(myArgs, config, logger)
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
    config = ec2publishimg.get_config(myArgs, logger)
    secret_key = ec2publishimg.get_secret_key(myArgs, config, logger)
    assert "BBBBBBBBBBBBBBBBBBBBBBBB" == secret_key


@patch('ec2publishimg.utils.get_from_config')
def test_get_secret_key_none(get_from_config_mock, caplog):
    get_from_config_mock.return_value = None

    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    myArgs.accountName = 'tester'
    config = ec2publishimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.get_secret_key(myArgs, config, logger)
    assert excinfo.value.code == 1
    assert 'Could not determine account secret access key' in caplog.text


def test_get_secret_key_exception():
    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2publishimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.get_secret_key(myArgs, config, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for main
@patch('ec2publishimg.ec2pubimg.EC2PublishImage._get_images')
def test_main_happy_path(get_images_mock, caplog):
    myImages = []
    myImage1 = {}
    myImage1['ImageId'] = "image_id1"
    myImage1['Name'] = "image_name1"
    myImage2 = {}
    myImage2['ImageId'] = "image_id2"
    myImage2['Name'] = "image_name2"
    myImages.append(myImage1)
    myImages.append(myImage2)

    get_images_mock.return_value = myImages

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--dry-run",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "image_name1",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "all",
      "--verbose"
    ]

    ec2publishimg.main(cli_args)
    assert "region1" in caplog.text
    assert "Published: image_id1" in caplog.text
    assert "Published: image_id2" in caplog.text
    assert "image_name1" in caplog.text
    assert "image_name2" in caplog.text
    assert "region1" in caplog.text


@patch('ec2publishimg.ec2pubimg.EC2PublishImage')
def test_main_happy_path2(ec2pubimg_mock, caplog):

    ec2PI = MagicMock()
    ec2PI.publish_images.return_value = None
    ec2pubimg_mock.return_value = ec2PI

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "image_name1",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "123456789123,",
      "--verbose"
    ]

    ec2publishimg.main(cli_args)


@patch('ec2publishimg.ec2pubimg.EC2PublishImage')
def test_main_constructor_exc(ec2pubimg_mock, caplog):

    def my_side_eff(
        access_key=None,
        allow_copy=False,
        image_id=None,
        image_name=None,
        image_name_fragment=None,
        image_name_match=None,
        secret_key=None,
        visibility=None,
        log_callback=None
    ):
        raise ec2publishimg.EC2PublishImgException

    ec2pubimg_mock.side_effect = my_side_eff

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "image_name1",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "123456789123,",
      "--verbose"
    ]

    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.main(cli_args)
    assert excinfo.value.code == 1


@patch('ec2publishimg.ec2pubimg.EC2PublishImage')
def test_main_exc1(ec2pubimg_mock, caplog):

    def my_side_eff():
        raise Exception('myException')

    ec2PI = MagicMock()
    ec2PI.publish_images.side_effect = my_side_eff
    ec2pubimg_mock.return_value = ec2PI

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "image_name1",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "123456789123,",
      "--verbose"
    ]

    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.main(cli_args)
    assert excinfo.value.code == 1
    assert 'myException' in caplog.text


@patch('ec2publishimg.ec2pubimg.EC2PublishImage')
def test_main_exc2(ec2pubimg_mock, caplog):

    def my_side_eff():
        raise ec2publishimg.EC2PublishImgException

    ec2PI = MagicMock()
    ec2PI.publish_images.side_effect = my_side_eff
    ec2pubimg_mock.return_value = ec2PI

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--allow-copy",
      "none",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "image_name1",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey",
      "--share-with",
      "123456789123,",
      "--verbose"
    ]

    with pytest.raises(SystemExit) as excinfo:
        ec2publishimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "EC2PublishImgException" in caplog.text
