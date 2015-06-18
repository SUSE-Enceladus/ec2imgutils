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

from .ec2UtilsExceptions import *


# -----------------------------------------------------------------------------
def check_account_keys(config, command_args):
    """Verify that API access keys are available"""
    if (command_args.accessKey and command_args.secretKey):
        # All data specified on the command line nothing to do
        return 1
    _basic_account_check(command_args)
    account = command_args.accountName
    acctName = generateConfigAccountName(account)
    accessKey = config.get_option(acctName, 'access_key_id')
    secretKey = config.get_option(acctName, 'secret_access_key')
    if accessKey and secretKey:
        # All data specified on the command line nothing to do
        return 1
    if command_args.accessKey and secretKey:
        # Combination of config and command line
        return 1
    if accessKey and command_args.secretKey:
        # Combination of config and command line
        return 1
    msg = 'Could not determine the access keys from data on command line '
    msg += 'and configuration file.'
    raise EC2AccountException(msg)


# -----------------------------------------------------------------------------
def check_ssh_resent(config, command_args):
    """Verify that an ssh key exists"""
    if (
            command_args.sshName and
            command_args.privateKey and
            os.path.exists(command_args.privateKey)):
        # All data specified on the command line nothing to do
        return 1
    _basicAccountCheck(command_args)
    account = command_args.accountName
    acctName = generateConfigAccountName(account)
    sshKeyName = config.get_option(acctName, 'ssh_key_name')
    sshPrivateKey = config.get_option(acctName, 'ssh_private_key')
    if sshKeyName and sshPrivateKey and os.path.exists(sshPrivateKey):
        # All the data is available from the specified account
        return 1
    if command_args.sshName and sshPrivateKey and os.path.exists(sshPrivateKey):
        # Key name from command line and private key from config
        return 1
    if (
            sshKeyName and
            command_args.privateKey and
            os.path.exists(command_args.privateKey)):
        # Key name from config private key from command line
        return 1
    regions = get_regions(command_args)
    for region in regions:
        if not config.has_section(region):
            msg = 'Could not find region %s in configuration file' % region
            raise EC2AccountException(msg)
        sshKeyName = config.get_option(region, 'ssh_key_name')
        sshPrivateKey = config.get_option(region, 'ssh_private_key')
        if sshKeyName and sshPrivateKey and os.path.exists(sshPrivateKey):
            # All the data is available from the specified account
            return 1
        if command_args.sshName and sshPrivateKey and os.path.exists(sshPrivateKey):
            # Key name from command line and private key from config
            return 1
        if (
                sshKeyName and
                command_args.privateKey and
                os.path.exists(command_args.privateKey)):
            # Key name from config private key from command line
            return 1


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
        type, value, tb = sys.exec_info()
        msg += '\n%s' % value.message
        raise EC2UtilsConfigFileParseException(msg)

    if not parsed:
        msg = 'Error parsing config file: %s' % configFilePath
        raise EC2ConfigFileParseException(msg)

    return config


# -----------------------------------------------------------------------------
def get_from_config(account, config, region, entry):
    """Retrieve anentry from the configuration"""
    value = None
    if region:
        region_name = generate_config_region_name(region)
        # Region config over rides default account configuration
        if config.has_option(region_name, entry):
            value = config.get(region_name, entry)

    if not value:
        if not account:
            msg = 'No account give missing value %s on command line'
            raise EC2AccountException(msg)

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
def _basic_ccount_check(command_args):
    """Basic check for account presense."""
    account = command_args.accountName
    if not account:
        msg = 'Cannot determine ssh key, no account given and not specified '
        msg += 'on command line'
        raise EC2AccountException(msg)
    acctName = generateConfigAccountName(account)
    if not config.has_section(acctName):
        msg = 'Could not find account %s in configuration file' % acctName
        raise EC2AccountExceptiong(msg)
    return 1
