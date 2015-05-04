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

import ConfigParser

from ec2utils.ec2UtilsExceptions import *

def getConfig(configFilePath):
    """Return a config object fr hte given file."""

    config = ConfigParser.RawConfigParser()
    parsed = None
    try:
        parsed = config.read(configFilePath)
    except:
        msg = 'Could not parse configuration file %s' %configFilePath
        type, value, tb = sys.exec_info()
        msg += '\n%s' %value.message
        raise EC2UtilsConfigFileParseException(msg)
		
    if not parsed:
        msg = 'Error parsing config file: %s' %configFilePath
        raise EC2ConfigFileParseException(msg)

    return config
