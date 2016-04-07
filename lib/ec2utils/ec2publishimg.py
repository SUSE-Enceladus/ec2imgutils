# Copyright 2015 SUSE LLC, Robert Schweikert
#
# This file is part of ec2publishimg.
#
# ec2publishimg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2publishimg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2publishimg. If not, see <http://www.gnu.org/licenses/>.

import boto3
import re

import ec2utilsutils as utils
from .ec2utils import EC2Utils
from .ec2UtilsExceptions import *


class EC2PublishImage(EC2Utils):
    """Publish/share EC2 image(s). Will also hide the image(s)"""

    # --------------------------------------------------------------------
    def __init__(
            self,
            access_key=None,
            image_id=None,
            image_name=None,
            image_name_fragment=None,
            image_name_match=None,
            secret_key=None,
            verbose=None,
            visibility='all'):
        EC2Utils.__init__(self)

        self.access_key = access_key
        self.image_id = image_id
        self.image_name = image_name
        self.image_name_fragment = image_name_fragment
        self.image_name_match = image_name_match
        self.secret_key = secret_key
        self.verbose = verbose
        self.visibility = visibility

        if self.visibility == 'all':
            self.publish_msg = '\tPublished: %s\t\t%s'
        elif self.visibility == 'none':
            self.publish_msg = '\tSet to private: %s\t\t%s'
        else:
            self.publish_msg = '\tShared: %s\t\t%s\t with: %s'

    # --------------------------------------------------------------------
    def _get_images(self):
        """Return a list of images that match the filter criteria"""
        self._connect()
        owned_images = self._get_owned_images() 
        if self.image_id:
            return utils.find_images_by_id(owned_images, self.image_id)
        elif self.image_name:
            return utils.find_images_by_name(owned_images, self.image_name)
        elif self.image_name_fragment:
            return utils.find_images_by_name_fragment(
                owned_images,
                self.image_name_fragment)
        elif self.image_name_match:
            try:
                return utils.find_images_by_name_regex_match(
                    owned_images,
                    self.image_name_match)
            except:
                msg = 'Unable to complie regular expression "%s"'
                msg = msg % self.image_name_match
                raise EC2PublishImgException(msg)

    # --------------------------------------------------------------------
    def _print_image_info(self, image):
        """Print a message about the image that would be modified"""
        if self.visibility == 'all' or self.visibility == 'none':
            print self.publish_msg % (image['ImageId'], image['Name'])
        else:
            print self.publish_msg % (
                        image['ImageId'],
                        image['Name'],
                        self.visibility
            )

    # --------------------------------------------------------------------
    def print_publish_info(self):
        """Print information about images that would be published"""
        images = self._get_images()
        for image in images:
            self._print_image_info(image)

    # --------------------------------------------------------------------
    def publish_images(self):
        """Publish the matching image(s)"""
        images = self._get_images()

        for image in images:
            if self.visibility == 'all':
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission',
                    OperationType='add',
                    UserGroups=['all']
                )
            elif self.visibility == 'none':
                launch_attributes = self._connect().describe_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission')['LaunchPermissions']
                launch_permission = {
                    'Remove': launch_attributes
                }
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    LaunchPermission=launch_permission
                )
            else:
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission',
                    OperationType='add',
                    UserIds=self.visibility.split(',')
                )
            if self.verbose:
                self._print_image_info(image)
