# Copyright (c) 2015 SUSE LLC, Robert Schweikert <rjschwei@suse.com>
#
# This file is part of ec2utilsbase.
#
# ec2utilsbase is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2utilsbase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2utilsbase.  If not, see <http://www.gnu.org/licenses/>.

import boto
import boto.ec2
import ConfigParser
import os
import re
import sys

try:
    from .ec2UtilsExceptions import *
except:
    from ec2UtilsExceptions import *


# -----------------------------------------------------------------------------
def check_account_keys(config, command_args):
    """Verify that API access keys are available"""
    if (command_args.accessKey and command_args.secretKey):
        # All data specified on the command line nothing to do
        return 1
    _basic_account_check(config, command_args)
    account = command_args.accountName
    account_name = generate_config_account_name(account)
    access_key = None
    if config.has_option(account_name, 'access_key_id'):
        access_key = config.get(account_name, 'access_key_id')
    secret_key = None
    if config.has_option(account_name, 'secret_access_key'):
        secret_key = config.get(account_name, 'secret_access_key')
    if access_key and secret_key:
        # All data specified on the command line nothing to do
        return 1
    if command_args.accessKey and secret_key:
        # Combination of config and command line
        return 1
    if access_key and command_args.secretKey:
        # Combination of config and command line
        return 1
    msg = 'Could not determine the access keys from data on command line '
    msg += 'and configuration file.'
    raise EC2AccountException(msg)


# ----------------------------------------------------------------------------
def find_images_by_id(images, image_id):
    """Return a list of images that mtch the given ID. By definition this
       is a list of one as IDs are unique."""
    matching_images = []
    for image in images:
        if image_id == image.id:
            matching_images.append(image)
            # The framework guarantees unique image IDs
            break

    return matching_images


# ----------------------------------------------------------------------------
def find_images_by_name(images, image_name):
    """Return a list of images that match the given name."""
    matching_images = []
    for image in images:
        if not image.name:
            print _no_name_warning(image)
            continue
        if image_name == image.name:
            matching_images.append(image)

    return matching_images


# ----------------------------------------------------------------------------
def find_images_by_name_fragment(images, image_name_fragment):
    """Return a list of images that match the given fragment in any part
       of the image name."""
    matching_images = []
    for image in images:
        if not image.name:
            print _no_name_warning(image)
            continue
        if image.name.find(image_name_fragment) != -1:
            matching_images.append(image)

    return matching_images


# ----------------------------------------------------------------------------
def find_images_by_name_regex_match(images, image_name_regex):
    """Return a list of images that match the given regular expression in
       their name."""
    matching_images = []
    image_name_exp = re.compile(image_name_regex)
    for image in images:
        if not image.name:
            print _no_name_warning(image)
            continue
        if image_name_exp.match(image.name):
            matching_images.append(image)

    return matching_images


# -----------------------------------------------------------------------------
def generate_config_account_name(account):
    """Generate the name of an account as it expected in the configuration"""
    return 'account-%s' % account


# -----------------------------------------------------------------------------
def generate_config_region_name(region):
    """Generate the name for a region as it is expected in the configuration"""
    return 'region-%s' % region


# -----------------------------------------------------------------------------
def get_config(configFilePath):
    """Return a config object fr hte given file."""

    config = ConfigParser.RawConfigParser()
    parsed = None
    try:
        parsed = config.read(configFilePath)
    except:
        msg = 'Could not parse configuration file %s' % configFilePath
        type, value, tb = sys.exc_info()
        msg += '\n%s' % value.message
        raise EC2ConfigFileParseException(msg)

    if not parsed:
        msg = 'Error parsing config file: %s' % configFilePath
        raise EC2ConfigFileParseException(msg)

    return config


# -----------------------------------------------------------------------------
def get_from_config(account, config, region, entry, cmd_line_arg):
    """Retrieve an entry from the configuration"""
    value = None
    if region:
        region_name = generate_config_region_name(region)
        # Region config over rides default account configuration
        if config.has_option(region_name, entry):
            value = config.get(region_name, entry)

    if not value:
        if not account:
            msg = 'No account given; missing command line argument %s'
            raise EC2AccountException(msg % cmd_line_arg)

        account_name = generate_config_account_name(account)
        try:
            value = config.get(account_name, entry)
        except:
            msg = 'Unable to get %s value from account section %s'
            raise EC2AccountException(msg % (entry, account))

    return value


# -----------------------------------------------------------------------------
def get_regions(command_args):
    """Return a list of connected regions if no regions are specified
       on the command line"""
    regions = None
    if command_args.regions:
        regions = command_args.regions.split(',')
    else:
        regions = []
        regs = boto.ec2.regions()
        for reg in regs:
            if reg.name in ['us-gov-west-1', 'cn-north-1']:
                if command_args.verbose:
                    print 'Not processing disconnected region: %s' % reg.name
                continue
            regions.append(reg.name)
    return regions


# -----------------------------------------------------------------------------
def _basic_account_check(config, command_args):
    """Basic check for account presense."""
    account = command_args.accountName
    if not account:
        msg = 'Cannot determine ssh key, no account given and not specified '
        msg += 'on command line'
        raise EC2AccountException(msg)
    acctName = generate_config_account_name(account)
    if not config.has_section(acctName):
        msg = 'Could not find account %s in configuration file' % acctName
        raise EC2AccountException(msg)
    return 1


# ----------------------------------------------------------------------------
def _no_name_warning(image):
    """Print a warning for images that have no name"""
    msg = 'WARNING: Found image with no name, ignoring for search results. '
    msg += 'Image ID: %s' % image.id
    print msg
