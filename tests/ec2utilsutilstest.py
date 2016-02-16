#!/usr/bin/python
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

import ConfigParser
import os
import sys

from nose.tools import *

this_path = os.path.dirname(os.path.abspath(__file__))
mod_path = this_path + os.sep + '../lib/ec2utils'
data_path = this_path + os.sep + 'data'
sys.path.insert(0, mod_path)

import ec2utilsutils as utils
from ec2UtilsExceptions import *


class Turncoat:
    pass


def test_check_account_keys_no_cmd_keys():
    """Test check_account_keys with the keys available in the config file"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = utils.get_config(config_file)
    command_args = Turncoat()
    command_args.accessKey = None
    command_args.secretKey = None
    command_args.accountName = 'tester'
    assert_equals(1, utils.check_account_keys(config, command_args))


def test_check_account_keys_cmd_access_key():
    """Test check_account_keys with the secrect key in the file and the
       access key on the command line."""
    config_file = data_path + os.sep + 'noaccesskey.cfg'
    config = utils.get_config(config_file)
    command_args = Turncoat()
    command_args.accessKey = 'AAAAAA'
    command_args.secretKey = None
    command_args.accountName = 'tester'
    assert_equals(1, utils.check_account_keys(config, command_args))


def test_check_account_keys_cmd_secret_key():
    """Test check_account_keys with the access key in the file and the
       secret key on the command line."""
    config_file = data_path + os.sep + 'nosecretkey.cfg'
    config = utils.get_config(config_file)
    command_args = Turncoat()
    command_args.accessKey = None
    command_args.secretKey = 'BBBBBBB'
    command_args.accountName = 'tester'
    assert_equals(1, utils.check_account_keys(config, command_args))


def test_check_account_keys_cmd_keys():
    """Test check_account_keys with the access and secret key on the
       command line."""
    config_file = data_path + os.sep + 'nokeys.cfg'
    config = utils.get_config(config_file)
    command_args = Turncoat()
    command_args.accessKey = 'AAAAAA'
    command_args.secretKey = 'BBBBBBB'
    command_args.accountName = 'tester'
    assert_equals(1, utils.check_account_keys(config, command_args))


@raises(EC2AccountException)
def test_check_account_keys_no_keys():
    """Test check_account_keys with no keys available."""
    config_file = data_path + os.sep + 'nokeys.cfg'
    config = utils.get_config(config_file)
    command_args = Turncoat()
    command_args.accessKey = None
    command_args.secretKey = None
    command_args.accountName = 'tester'
    utils.check_account_keys(config, command_args)


def test_find_images_by_id_find_one():
    """Test find_images_by_id finds an image"""
    images = []
    for cnt in range(2):
        image = Turncoat()
        image.id = cnt
        images.append(image)
    found_images = utils.find_images_by_id(images, 1)
    assert_equals(1, len(found_images))
    assert_equals(1, found_images[0].id)


def test_find_images_by_id_find_none():
    """Test find_images_by_id finds nothing and does not error"""
    images = []
    for cnt in range(2):
        image = Turncoat()
        image.id = cnt
        images.append(image)
    found_images = utils.find_images_by_id(images, 5)
    assert_equals(0, len(found_images))


def test_find_images_by_name_find_some():
    """Test find_images_by_name finds images"""
    images = _get_test_images()
    image = Turncoat()
    image.name = 'testimage-1'
    images.append(image)
    found_images = utils.find_images_by_name(images, 'testimage-1')
    assert_equals(2, len(found_images))
    assert_equals('testimage-1', found_images[1].name)


def test_find_images_by_name_find_none():
    """Test find_images_by_name finds nothing and does not error"""
    images = _get_test_images()
    found_images = utils.find_images_by_name(images, 'test')
    assert_equals(0, len(found_images))


def test_find_images_by_name_fragment_find_some():
    """Test find_images_by_name_fragment finds images"""
    images = []
    image = Turncoat()
    image.name = 'this-is-different'
    images.append(image)
    image = Turncoat()
    image.name = 'find-this'
    images.append(image)
    image = Turncoat
    image.name = 'testimg'
    images.append(image)
    found_images = utils.find_images_by_name_fragment(images, 'this')
    assert_equals(2, len(found_images))


def test_find_images_by_name_fragment_find_none():
    """Test find_images_by_name_fragment finds nothing and does not error"""
    images = _get_test_images()
    found_images = utils.find_images_by_name_fragment(images, 'foo')
    assert_equals(0, len(found_images))


def test_find_images_by_name_regex_match_find_some():
    """Test find_images_by_name_regex_match finds images"""
    images = _get_test_images()
    found_images = utils.find_images_by_name_regex_match(images, '^test')
    assert_equals(2, len(found_images))


def test_find_images_by_name_regex_match_find_none():
    """Test find_images_by_name_regex_match finds  nothing and
       does not error"""
    images = _get_test_images()
    found_images = utils.find_images_by_name_regex_match(images, '^-1')
    assert_equals(0, len(found_images))


@raises(Exception)
def test_find_images_by_name_regex_match_invalid_re():
    """Test find_images_by_name_regex_match throws with invalid expression"""
    images = _get_test_images()
    found_images = utils.find_images_by_name_regex_match(images, 't*{2}')


def test_generate_config_account_name():
    """Test generate_config_account_name returns the expected name"""
    expected = 'account-foo'
    account_name = utils.generate_config_account_name('foo')
    assert_equals(expected, account_name)


def test_generate_config_region_name():
    """Test generate_config_region_name returns the expected name"""
    expected = 'region-bar'
    region_name = utils.generate_config_region_name('bar')
    assert_equals(expected, region_name)


@raises(EC2ConfigFileParseException)
def test_get_config_invalid():
    """Test get_config with an invalid configuration file"""
    config_file = data_path + os.sep + 'invalid.cfg'
    config = utils.get_config(config_file)


def test_get_from_config_from_account():
    """Test get_from_config returns expected data form an account"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = utils.get_config(config_file)
    expected = 'AAAAAAAAAAAAAA'
    access_key_id = utils.get_from_config(
        'tester',
        config,
        None,
        'access_key_id',
        '--access-id')
    assert_equals(expected, access_key_id)


def test_get_from_config_region_override():
    """Test get_from_config returns expected data if account setting
       is overridden ina a region"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = utils.get_config(config_file)
    expected = 'east-region'
    ssh_key_name = utils.get_from_config(
        'tester',
        config,
        'us-east-1',
        'ssh_key_name',
        '--ssh-key-pair')
    assert_equals(expected, ssh_key_name)


@raises(EC2AccountException)
def test_get_from_config_invalid_account_name():
    """Test get_from_config throws if an invalid account name is given"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = utils.get_config(config_file)
    ssh_key_name = utils.get_from_config(
        'foo',
        config,
        None,
        'ssh_key_name',
        '--ssh-key-pair')


@raises(EC2AccountException)
def test_get_from_config_invalid_account_name():
    """Test get_from_config throws if no account name is given"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = utils.get_config(config_file)
    ssh_key_name = utils.get_from_config(
        None,
        config,
        None,
        'ssh_key_name',
        '--ssh-key-pair')


def test_get_regions_from_cmd():
    """Test get_regions returns expected result for given command"""
    command_args = Turncoat()
    command_args.regions = 'milk,cookies,chocolate'
    expected = command_args.regions.split(',')
    regions = utils.get_regions(command_args)
    assert_equals(expected, regions)


# --------------------------------------------------------------------
# Helpers
def _get_test_images():
    images = []
    base_name = 'testimage-'
    for cnt in range(2):
        image = Turncoat()
        image.name = base_name + '%d' % cnt
        images.append(image)

    return images
