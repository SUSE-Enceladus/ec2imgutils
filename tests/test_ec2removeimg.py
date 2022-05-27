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
import io
import sys
import os

from unittest.mock import patch, MagicMock

# Hack to get the script without the .py imported for testing
from importlib.machinery import SourceFileLoader

ec2removeimg = SourceFileLoader(
    'ec2removeimg',
    './ec2removeimg'
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
      "--all",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--confirm",
      "--preserve-snap",
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
    parsed_args = ec2removeimg.parse_args(cli_args)
    assert parsed_args.accountName == "testAccName"
    assert parsed_args.accessKey == "testAccId"
    assert parsed_args.all is True
    assert parsed_args.dryRun is True
    assert parsed_args.configFilePath == "/path/to/configuration/file"
    assert parsed_args.imageName == "testImageName"
    assert parsed_args.confirm is True
    assert parsed_args.preserveSnap is True
    assert parsed_args.regions == "region1,region2,region3"
    assert parsed_args.secretKey == "testSecretKey"
    assert parsed_args.verbose is True


# --------------------------------------------------------------------
# Tests for arguments exclusive group
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--image-name",
      "testImageName",
      "--image-id",
      "testImageAMIid",
      "--confirm",
      "--preserve-snap",
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
def test_image_arguments_exclusive_group(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.parse_args(cli_args)
    assert excinfo.value.code == 2


# --------------------------------------------------------------------
# Tests for mandatory arguments provided
test_cli_args_data = [
    (["--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--dry-run",
      "--file",
      "/path/to/configuration/file",
      "--confirm",
      "--preserve-snap",
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
def test_image_arguments_absent(cli_args):
    with pytest.raises(SystemExit) as excinfo:
        parsed_args = ec2removeimg.parse_args(cli_args)
        ec2removeimg.check_required_arguments(parsed_args, logger)
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
    parsed_args = ec2removeimg.parse_args(cli_args)
    if expected_exit:
        with pytest.raises(SystemExit) as excinfo:
            ec2removeimg.get_config(parsed_args, logger)
        assert excinfo.value.code == 1


def test_get_invalid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'invalid.cfg'
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.get_config(myArgs, logger)
    assert excinfo.value.code == 1


def test_get_valid_config():
    class Args:
        configFilePath = ""
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2removeimg.get_config(myArgs, logger)
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
    config = ec2removeimg.get_config(myArgs, logger)
    access_key = ec2removeimg.get_access_key(myArgs, config, logger)
    assert "AAAAAAAAAAAAAA" == access_key


def test_get_access_key_exception():
    class Args:
        configFilePath = ''
        accessKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2removeimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.get_access_key(myArgs, config, logger)
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
    config = ec2removeimg.get_config(myArgs, logger)
    secret_key = ec2removeimg.get_secret_key(myArgs, config, logger)
    assert "BBBBBBBBBBBBBBBBBBBBBBBB" == secret_key


def test_get_secret_key_exception():
    class Args:
        configFilePath = ''
        secretKey = ''
        accountName = ''
    myArgs = Args()
    myArgs.configFilePath = data_path + os.sep + 'complete.cfg'
    config = ec2removeimg.get_config(myArgs, logger)
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.get_secret_key(myArgs, config, logger)
    assert excinfo.value.code == 1


# --------------------------------------------------------------------
# Tests for main
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "testImageName",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_dry_run(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--dry-run",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "testImageName",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)
    assert "region1" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text
    assert "testImageName" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_id(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_id_dry_run(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--dry-run",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)
    assert "region1" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text
    assert "testImageName" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_frag(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-frag",
      "Not",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_frag_dry_run(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--dry-run",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-frag",
      "Not",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)
    assert "region1" in caplog.text
    assert "ami-000cc31892067693b" in caplog.text
    assert "NotTestImage" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*Name$",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_dry_run(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--dry-run",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*Name$",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)
    assert "region1" in caplog.text
    assert "ami-000cc31892067693a" in caplog.text
    assert "testImageName" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_delete_snap(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name",
      "testImageName",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_exception(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*est.*",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "Image ambiguity" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_no_match(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      "^NOTMATCHING$",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    ec2removeimg.main(cli_args)
    assert "No images to remove found" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_no_proper_regex(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      "^[NOT$",
      "--preserve-snap",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "Unable to compile regular expression" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_no_block_device(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images_without_device_mappings()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "has no device map" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_no_ebs(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images_without_ebs()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "is not EBS backed" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_no_snapid(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images_without_snapid()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    assert excinfo.value.code == 1
    assert "No snapshot found for image" in caplog.text


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_confirm_yes(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--confirm",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    sys.stdin = io.StringIO("yes\n")
    ec2removeimg.main(cli_args)
    sys.stdin = sys.__stdin__


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_confirm_no(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--confirm",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    sys.stdin = io.StringIO("no\n")
    ec2removeimg.main(cli_args)
    sys.stdin = sys.__stdin__


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_confirm_wrong(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--confirm",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-id",
      "ami-000cc31892067693a",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    sys.stdin = io.StringIO("whatever\n")
    with pytest.raises(SystemExit) as excinfo:
        ec2removeimg.main(cli_args)
    sys.stdin = sys.__stdin__
    assert excinfo.value.code == 1


@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._get_owned_images')
@patch('ec2removeimg.ec2rmimg.EC2RemoveImage._connect')
def test_remove_images_filtering_by_name_match_confirm_no_yes(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    ec2 = MagicMock()
    ec2.deregister_image.return_value = None
    ec2.delete_snapshot.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = \
        mock_get_owned_images()

    cli_args = [
      "--account",
      "testAccName",
      "--access-id",
      "testAccId",
      "--all",
      "--confirm",
      "--file",
      data_path + os.sep + 'complete.cfg',
      "--image-name-match",
      ".*",
      "--regions",
      "region1",
      "--secret-key",
      "testSecretKey"
    ]
    sys.stdin = io.StringIO("no\nyes\n")
    ec2removeimg.main(cli_args)
    sys.stdin = sys.__stdin__


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
    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    return myImages


def mock_get_owned_images_without_device_mappings():
    myImage1 = {}
    myImage1["Architecture"] = "x86_64"
    myImage1["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage1["ImageId"] = "ami-000cc31892067693a"
    myImage1["Name"] = "testImageName"

    myImage2 = {}
    myImage2["Architecture"] = "x86_64"
    myImage2["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage2["ImageId"] = "ami-000cc31892067693b"
    myImage2["Name"] = "NotTestImage"

    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    return myImages


def mock_get_owned_images_without_ebs():
    myImage1 = {}
    myImage1["Architecture"] = "x86_64"
    myImage1["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage1["ImageId"] = "ami-000cc31892067693a"
    myImage1["Name"] = "testImageName"
    bdmI1 = {}
    bdmI1["DeviceName"] = "/dev/sda1"
    myImage1["BlockDeviceMappings"] = []
    myImage1["BlockDeviceMappings"].append(bdmI1)

    myImage2 = {}
    myImage2["Architecture"] = "x86_64"
    myImage2["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage2["ImageId"] = "ami-000cc31892067693b"
    myImage2["Name"] = "NotTestImage"
    bdmI2 = {}
    bdmI2["DeviceName"] = "/dev/sda1"
    myImage2["BlockDeviceMappings"] = []
    myImage2["BlockDeviceMappings"].append(bdmI2)
    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    return myImages


def mock_get_owned_images_without_snapid():
    myImage1 = {}
    myImage1["Architecture"] = "x86_64"
    myImage1["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage1["ImageId"] = "ami-000cc31892067693a"
    myImage1["Name"] = "testImageName"
    myI1Ebs = {}
    myI1Ebs["DeleteOnTermination"] = True
    myI1Ebs["VolumeSize"] = 10
    myI1Ebs["VolumeType"] = "gp3"
    myI1Ebs["Encrypted"] = False
    bdmI1 = {}
    bdmI1["DeviceName"] = "/dev/sda1"
    bdmI1["Ebs"] = myI1Ebs
    myImage1["BlockDeviceMappings"] = []
    myImage1["BlockDeviceMappings"].append(bdmI1)

    myImage2 = {}
    myImage2["Architecture"] = "x86_64"
    myImage2["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage2["ImageId"] = "ami-000cc31892067693b"
    myImage2["Name"] = "NotTestImage"
    myI2Ebs = {}
    myI2Ebs["DeleteOnTermination"] = True
    myI2Ebs["VolumeSize"] = 10
    myI2Ebs["VolumeType"] = "gp3"
    myI2Ebs["Encrypted"] = False
    bdmI2 = {}
    bdmI2["DeviceName"] = "/dev/sda1"
    bdmI2["Ebs"] = myI2Ebs
    myImage2["BlockDeviceMappings"] = []
    myImage2["BlockDeviceMappings"].append(bdmI2)
    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    return myImages
