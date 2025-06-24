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
from ec2imgutils.ec2imgutilsExceptions import EC2UndeprecateImgException


class EC2UndeprecateImg(EC2ImgUtils):
    """
    Undeprecate EC2 image(s) removing the image tagging of 3 tags,
     Deprecated on, Removal date, and Replacement image.
    """

    def __init__(
            self,
            access_key=None,
            undeprecation_image_id=None,
            undeprecation_image_name=None,
            undeprecation_image_name_fragment=None,
            undeprecation_image_name_match=None,
            image_virt_type=None,
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
        self.undeprecation_image_id = undeprecation_image_id
        self.undeprecation_image_name = undeprecation_image_name
        self.undeprecation_image_name_fragment = \
            undeprecation_image_name_fragment
        self.undeprecation_image_name_match = undeprecation_image_name_match
        self.image_virt_type = image_virt_type
        self.public_only = public_only
        self.secret_key = secret_key

    # ---------------------------------------------------------------------
    def _find_images_by_id(self, image_id, filter_replacement_image=None):
        """Find images by ID match"""
        my_images = self._get_all_type_match_images(filter_replacement_image)
        return utils.find_images_by_id(my_images, image_id)

    # ---------------------------------------------------------------------
    def _find_images_by_name(self, image_name, filter_replacement_image=None):
        """Find images by exact name match"""
        my_images = self._get_all_type_match_images(filter_replacement_image)
        return utils.find_images_by_name(my_images, image_name, self.log)

    # ---------------------------------------------------------------------
    def _find_images_by_name_fragment(
            self,
            name_fragment,
            filter_replacement_image=None):
        """Find images by string matching of the fragment with the name"""
        my_images = self._get_all_type_match_images(filter_replacement_image)
        return utils.find_images_by_name_fragment(
            my_images,
            name_fragment,
            self.log
        )

    # ---------------------------------------------------------------------
    def _find_images_by_name_regex_match(
            self,
            expression,
            filter_replacement_image=None):
        """Find images by match the name with the given regular expression"""
        my_images = self._get_all_type_match_images(filter_replacement_image)
        return utils.find_images_by_name_regex_match(
            my_images,
            expression,
            self.log
        )

    # ---------------------------------------------------------------------
    def _format_date(self, date):
        """Format the date to YYYYMMDD"""

        return date.strftime('%Y%m%d')

    # ---------------------------------------------------------------------
    def _get_all_type_match_images(self, filter_replacement_image=None):
        """Get all images that match thespecified virtualization type.
           All images owned by the account if not type is specified."""
        images = []
        my_images = self._get_owned_images()
        for image in my_images:
            should_append_virt_type = False
            should_append_public_only = False
            if filter_replacement_image:
                if image['ImageId'] == self.replacement_image_id:
                    msg = 'Ignore replacement image as potential target '
                    msg += 'for deprecation.'
                    self.log.debug(msg)
                    continue
            # Check for virt_type condition if specified
            if self.image_virt_type:
                if self.image_virt_type == image['VirtualizationType']:
                    should_append_virt_type = True
                else:
                    # cond specified and image not matching, moving on
                    continue

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
                self.image_virt_type and
                self.public_only and
                should_append_virt_type and
                should_append_public_only
            ):
                images.append(image)
            elif (
                self.image_virt_type and
                should_append_virt_type
            ):
                images.append(image)
            elif (
                self.public_only and
                should_append_public_only
            ):
                images.append(image)
            elif (
                not self.image_virt_type and
                not self.public_only
            ):
                images.append(image)
        return images

    # ---------------------------------------------------------------------
    def _get_images_to_undeprecate(self):
        """Find images to undeprecate"""
        images = None
        if self.undeprecation_image_id:
            images = self._find_images_by_id(self.undeprecation_image_id, True)
        elif self.undeprecation_image_name:
            images = self._find_images_by_name(
                self.undeprecation_image_name, True)
        elif self.undeprecation_image_name_fragment:
            images = self._find_images_by_name_fragment(
                self.undeprecation_image_name_fragment, True)
        elif self.undeprecation_image_name_match:
            images = self._find_images_by_name_regex_match(
                self.undeprecation_image_name_match, True)
        else:
            msg = 'No undeprecation image condition set. Should not reach '
            msg += 'this point.'
            raise EC2UndeprecateImgException(msg)

        return images

    # ---------------------------------------------------------------------
    def undeprecate_images(self):
        """Undeprecate images in the connected region"""
        self._connect()
        images = self._get_images_to_undeprecate()
        if not images:
            self.log.debug('No images to undeprecate found')
            return False

        self.log.debug(
            'Undeprecating images in region: {}'.format(self.region)
        )

        ec2 = self._connect()
        for image in images:
            existing_tags = image.get('Tags')
            not_tagged = False
            if not existing_tags:
                msg = '\t\tImage %s not tagged, skipping'
                self.log.debug(msg % image['ImageId'])
                not_tagged = True

            if not_tagged:
                continue

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

            ec2.remove_tags(
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
    def print_undeprecation_info(self):
        """Print information about the images that would be undeprecated."""
        self._connect()
        images = self._get_images_to_undeprecate()
        if not images:
            self.log.info('No images to undeprecate found')
            return True

        self.log.info(
            'Would undeprecate images in region: {}'.format(self.region)
        )

        self.log.info('\tImages to undeprecate:\n\t\tID\t\t\t\tName')
        for image in images:
            self.log.info('\t\t%s\t%s' % (image['ImageId'], image['Name']))

        return True
