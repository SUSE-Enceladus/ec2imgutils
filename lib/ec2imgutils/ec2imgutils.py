# Copyright (c) 2018 SUSE LLC
#
# This file is part of ec2imgutils.
#
# ec2imgutils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2imgutils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2imgutils.ase.  If not, see <http://www.gnu.org/licenses/>.

import boto3
import logging

from ec2imgutils.ec2imgutilsExceptions import EC2ConnectionException


class EC2ImgUtils:
    """Base class for EC2 Image Utilities"""

    def __init__(
        self,
        log_level=logging.INFO,
        log_callback=None,
        ec2_client=None
    ):

        self.region = None
        self.session_token = None

        if log_callback:
            self.log = log_callback
        else:
            logger = logging.getLogger('ec2imgutils')
            logger.setLevel(log_level)
            self.log = logger

        try:
            self.log_level = self.log.level
        except AttributeError:
            self.log_level = self.log.logger.level  # LoggerAdapter

        self.durable_ec2_client = ec2_client

    # ---------------------------------------------------------------------
    def _connect(self):
        """Connect to EC2"""

        # Allow dependency injection for easier testing
        if self.durable_ec2_client:
            return self.durable_ec2_client

        ec2 = None
        if self.region:
            if self.session_token:
                ec2 = boto3.client(
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    aws_session_token=self.session_token,
                    region_name=self.region,
                    service_name='ec2'
                )
            else:
                session = boto3.session.Session()
                ec2 = session.client(
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
    def _set_access_keys(self):
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

        self.log.debug('Using EC2 region: {}'.format(region))
        self.region = region

        return True
