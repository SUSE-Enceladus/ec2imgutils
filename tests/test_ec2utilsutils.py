#!/usr/bin/python3
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

import logging
import os
import pytest

from ec2imgutils import ec2utils
from ec2imgutils.ec2imgutilsExceptions import (
    EC2AccountException,
    EC2ConfigFileParseException,
)

this_path = os.path.dirname(os.path.abspath(__file__))
data_path = this_path + os.sep + 'data'

logger = logging.getLogger('ec2imgutils')
logger.setLevel(logging.INFO)


class Turncoat:
    pass


def test_find_images_by_id_find_one():
    """Test find_images_by_id finds an image"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_id(images, 1)
    assert 1 == len(found_images)
    assert 1 == found_images[0]['ImageId']


def test_find_images_by_id_find_none():
    """Test find_images_by_id finds nothing and does not error"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_id(images, 5)
    assert 0 == len(found_images)


def test_find_images_by_name_find_some():
    """Test find_images_by_name finds images"""
    images = _get_test_images()
    image = {}
    image['Name'] = 'testimage-1'
    images.append(image)
    found_images = ec2utils.find_images_by_name(images, 'testimage-1', logger)
    assert 2 == len(found_images)
    assert 'testimage-1' == found_images[1]['Name']


def test_find_images_by_name_pending_image():
    """
    Test find_images_by_name does not raise if an image is pending.

    If Status is pending image will not have a name key.
    """
    images = _get_test_images()
    image = {}
    image['Status'] = 'pending'
    image['ImageId'] = 'testimage-3'
    images.append(image)
    ec2utils.find_images_by_name(images, 'testimage-1', logger)


def test_find_images_by_name_find_none():
    """Test find_images_by_name finds nothing and does not error"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_name(images, 'test', logger)
    assert 0 == len(found_images)


def test_find_images_by_name_fragment_find_some():
    """Test find_images_by_name_fragment finds images"""
    images = []
    image = {}
    image['Name'] = 'this-is-different'
    images.append(image)
    image = {}
    image['Name'] = 'find-this'
    images.append(image)
    image = {}
    image['Name'] = 'testimg'
    images.append(image)
    found_images = ec2utils.find_images_by_name_fragment(
        images,
        'this',
        logger
    )
    assert 2 == len(found_images)


def test_find_images_by_name_fragment_find_none():
    """Test find_images_by_name_fragment finds nothing and does not error"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_name_fragment(
        images,
        'foo',
        logger
    )
    assert 0 == len(found_images)


def test_find_images_by_name_regex_match_find_some():
    """Test find_images_by_name_regex_match finds images"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_name_regex_match(
        images,
        '^test',
        logger
    )
    assert 2 == len(found_images)


def test_find_images_by_name_regex_match_find_none():
    """Test find_images_by_name_regex_match finds  nothing and
       does not error"""
    images = _get_test_images()
    found_images = ec2utils.find_images_by_name_regex_match(
        images,
        '^-1',
        logger
    )
    assert 0 == len(found_images)


def test_find_images_by_name_regex_match_invalid_re():
    """Test find_images_by_name_regex_match throws with invalid expression"""
    images = _get_test_images()

    with pytest.raises(Exception):
        ec2utils.find_images_by_name_regex_match(
            images,
            't*{2}',
            logger
        )


def test_generate_config_account_name():
    """Test generate_config_account_name returns the expected name"""
    expected = 'account-foo'
    account_name = ec2utils.generate_config_account_name('foo')
    assert expected == account_name


def test_generate_config_region_name():
    """Test generate_config_region_name returns the expected name"""
    expected = 'region-bar'
    region_name = ec2utils.generate_config_region_name('bar')
    assert expected == region_name


def test_get_config_invalid():
    """Test get_config with an invalid configuration file"""
    config_file = data_path + os.sep + 'invalid.cfg'

    with pytest.raises(EC2ConfigFileParseException):
        ec2utils.get_config(config_file)


def test_get_from_config_from_account():
    """Test get_from_config returns expected data form an account"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = ec2utils.get_config(config_file)
    expected = 'AAAAAAAAAAAAAA'
    access_key_id = ec2utils.get_from_config(
        'tester',
        config,
        None,
        'access_key_id',
        '--access-id')
    assert expected == access_key_id


def test_get_from_config_region_override():
    """Test get_from_config returns expected data if account setting
       is overridden ina a region"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = ec2utils.get_config(config_file)
    expected = 'east-region'
    ssh_key_name = ec2utils.get_from_config(
        'tester',
        config,
        'us-east-1',
        'ssh_key_name',
        '--ssh-key-pair')
    assert expected == ssh_key_name


def test_get_from_config_invalid_account_name():
    """Test get_from_config throws if an invalid account name is given"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = ec2utils.get_config(config_file)

    with pytest.raises(EC2AccountException):
        ec2utils.get_from_config(
            'foo',
            config,
            None,
            'ssh_key_name',
            '--ssh-key-pair')


def test_get_from_config_no_account_name():
    """Test get_from_config throws if no account name is given"""
    config_file = data_path + os.sep + 'complete.cfg'
    config = ec2utils.get_config(config_file)

    with pytest.raises(EC2AccountException):
        ec2utils.get_from_config(
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
    regions = ec2utils.get_regions(command_args, '123', '456')
    assert expected == regions


# --------------------------------------------------------------------
# Helpers
def _get_test_images():
    images = []
    base_name = 'testimage-'
    for cnt in range(2):
        image = {}
        image['ImageId'] = cnt
        image['Name'] = base_name + '%d' % cnt
        images.append(image)

    return images
