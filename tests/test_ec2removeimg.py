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
