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

import boto3
import ConfigParser
import os

from .ec2UtilsExceptions import *


class EC2Utils:
    """Base class for EC2 Utilities"""

    def __init__(self):

        self.region = None
        self.verbose = None

    # ---------------------------------------------------------------------
    def _connect(self):
        """Connect to EC2"""

        ec2 = None
        if self.region:
            ec2 = boto3.client(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                service_name='ec2'
            )
        else:
            self.region = 'UNKNOWN'

        if not ec2:
            msg = 'Could not connect to region: %s ' % self.region
            raise EC2ConnectionException(msg)

        return ec2

    # ---------------------------------------------------------------------
    def _get_owned_images(self):
        """Return the list of images owned by the account used for
           uploading"""
        return self._connect().describe_images(Owners=['self'])['Images']
    
    # ---------------------------------------------------------------------
    def _set_access_keys():
        """Set the access keys for the connection"""
        if not self.access_key:
            self.access_key = self.config.get_option(self.account,
                                                     'access_key_id')
        if not self.secret_key:
            self.secret_key = self.config.get_option(self.account,
                                                     'secret_access_key')

    # ---------------------------------------------------------------------
    def set_region(self, region):
        """Set the region that should be used."""
        if self.region and self.region == region:
            return True

        if self.verbose:
            print 'Using EC2 region: ', region
            
        self.region = region

        return True
