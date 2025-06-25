# Copyright 2025 SUSE LLC
#
# This file is part of ec2imgutils
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
# along with ec2deprecateimg. If not, see <http://www.gnu.org/licenses/>.

import logging

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2DisableImgDeprecationException


class EC2DisableImgDeprecation(EC2ImgUtils):
    """
    Disables the deprecation of EC2 image(s) removing the image tagging of
    3 tags, Deprecated on, Removal date, and Replacement image. Additionally
    runs the disable_deprecation operation in EC2 platform for the images.
    """

    def __init__(
            self,
            access_key=None,
            image_id=None,
            image_name=None,
            public_only=None,
            secret_key=None,
            log_level=logging.INFO,
            log_callback=None
    ):
        EC2ImgUtils.__init__(
            self,
            log_level=log_level,
            log_callback=log_callback
        )

        self.access_key = access_key
        self.image_id = image_id
        self.image_name = image_name
        self.public_only = public_only
        self.secret_key = secret_key

    # ---------------------------------------------------------------------
    def _find_images_by_id(self, image_id):
        """Find images by ID match"""
        my_images = self._get_all_type_match_images()
        return utils.find_images_by_id(my_images, image_id)

    # ---------------------------------------------------------------------
    def _find_images_by_name(self, image_name):
        """Find images by exact name match"""
        my_images = self._get_all_type_match_images()
        return utils.find_images_by_name(my_images, image_name, self.log)

    # ---------------------------------------------------------------------
    def _get_all_type_match_images(self):
        """
        Get all images owned by the account that match the public_only flag
        if specified, else returns all images owned by the account."""
        images = []
        my_images = self._get_owned_images()
        for image in my_images:
            should_append_public_only = False

            # Check for public_only condition if specified
            if self.public_only:
                launch_attributes = self._connect().describe_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission')['LaunchPermissions']
                launch_permission = None
                if launch_attributes:
                    launch_permission = launch_attributes[0].get('Group', None)
                if launch_permission == 'all':
                    should_append_public_only = True
                else:
                    # cond specified and image not matching, moving on
                    continue

            # Append the image once to the list of images to be processed
            # if a filter was configured and the image matched it
            if (
                self.public_only and
                should_append_public_only
            ):
                images.append(image)
            elif not self.public_only:
                images.append(image)
        return images

    # ---------------------------------------------------------------------
    def _get_images_to_disable_deprecation(self):
        """Find images to disable deprecation"""
        images = None
        if self.image_id:
            images = self._find_images_by_id(
                self.image_id
            )
        elif self.image_name:
            images = self._find_images_by_name(
                self.image_name
            )
        else:
            msg = 'No image condition set to disable deprecation. Should not '
            msg += 'reach this point.'
            raise EC2DisableImgDeprecationException(msg)

        return images

    # ---------------------------------------------------------------------
    def disable_images_deprecation(self):
        """Disables deprecation for images in the connected region"""
        self._connect()
        images = self._get_images_to_disable_deprecation()
        if not images:
            self.log.debug('No images found to disable deprecation.')
            return False

        self.log.debug(
            'Disabling deprecation images in region: {}'.format(self.region)
        )

        ec2 = self._connect()
        for image in images:
            existing_tags = image.get('Tags')
            tagged = True
            if not existing_tags:
                msg = '\t\tImage %s not tagged, skipping tag removal'
                self.log.debug(msg % image['ImageId'])
                tagged = False

            tags_to_remove = [
                {
                    'Key': 'Deprecated on'
                },
                {
                    'Key': 'Removal date'
                },
                {
                    'Key': 'Replacement image'
                }
            ]

            if tagged:
                ec2.delete_tags(
                    Resources=[image['ImageId']], Tags=tags_to_remove
                )
                self.log.debug(
                    '\t\tUntagged:%s\t%s' % (image['ImageId'], image['Name'])
                )

            # There is a difference in terminology. In EC2 deprecated means
            # an image cannot be used anymore by new users, this is similar
            # to a deletion. For ec2imgutils deprecation means an image should
            # no longer be used. Therefore we unset the deprecation date in AWS
            ec2.disable_image_deprecation(
                ImageId=image['ImageId'],
            )
            self.log.debug(
                '\t\tDisabled deprecation:%s\t%s' % (
                    image['ImageId'],
                    image['Name']
                )
            )

    # ---------------------------------------------------------------------
    def print_disable_images_deprecation_info(self):
        """
        Print information about the images that would get their deprecation
        disabled.
        """
        self._connect()
        images = self._get_images_to_disable_deprecation()
        if not images:
            self.log.info('No images found to disable deprecation')
            return True

        self.log.info(
            'Would disable deprecation for images in region: {}'.format(
                self.region
            )
        )

        self.log.info('\tImages to disable deprecation:\n\t\tID\t\t\t\tName')
        for image in images:
            self.log.info('\t\t%s\t%s' % (image['ImageId'], image['Name']))

        return True
