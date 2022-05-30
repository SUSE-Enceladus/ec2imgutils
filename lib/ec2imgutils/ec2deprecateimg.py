# Copyright 2021 SUSE LLC
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

import datetime
import dateutil.relativedelta
import logging

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2DeprecateImgException


class EC2DeprecateImg(EC2ImgUtils):
    """Deprecate EC2 image(s) by tagging the image with 3 tags, Deprecated on,
       Removal date, and Replacement image."""

    def __init__(
            self,
            access_key=None,
            deprecation_date='',
            deprecation_period=6,
            deprecation_image_id=None,
            deprecation_image_name=None,
            deprecation_image_name_fragment=None,
            deprecation_image_name_match=None,
            force=None,
            image_virt_type=None,
            public_only=None,
            replacement_image_id=None,
            replacement_image_name=None,
            replacement_image_name_fragment=None,
            replacement_image_name_match=None,
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
        self.deprecation_period = deprecation_period
        self.deprecation_image_id = deprecation_image_id
        self.deprecation_image_name = deprecation_image_name
        self.deprecation_image_name_fragment = deprecation_image_name_fragment
        self.deprecation_image_name_match = deprecation_image_name_match
        self.force = force
        self.image_virt_type = image_virt_type
        self.public_only = public_only
        self.replacement_image_id = replacement_image_id
        self.replacement_image_name = replacement_image_name
        self.replacement_image_name_fragment = replacement_image_name_fragment
        self.replacement_image_name_match = replacement_image_name_match
        self.secret_key = secret_key
        try:
            self._set_deprecation_date(deprecation_date)
            self._set_deletion_date()
        except Exception:
            raise
        self.replacement_image_tag = None

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
    def _get_images_to_deprecate(self):
        """Find images to deprecate"""
        images = None
        if self.deprecation_image_id:
            images = self._find_images_by_id(self.deprecation_image_id, True)
        elif self.deprecation_image_name:
            images = self._find_images_by_name(
                self.deprecation_image_name, True)
        elif self.deprecation_image_name_fragment:
            images = self._find_images_by_name_fragment(
                self.deprecation_image_name_fragment, True)
        elif self.deprecation_image_name_match:
            images = self._find_images_by_name_regex_match(
                self.deprecation_image_name_match, True)
        else:
            msg = 'No deprecation image condition set. Should not reach '
            msg += 'this point.'
            raise EC2DeprecateImgException(msg)

        return images

    # ---------------------------------------------------------------------
    def _set_deletion_date(self):
        """Set the date when the deprecation period expires"""
        dep_date = datetime.datetime.strptime(self.deprecation_date, '%Y%m%d')
        expire = dep_date + dateutil.relativedelta.relativedelta(
            months=+self.deprecation_period)
        self.deletion_date = self._format_date(expire)

    # ---------------------------------------------------------------------
    def _set_deprecation_date(self, deprecation_date=''):
        """Set the deprecation date provided in the YYYYMMDD format"""
        dep_date = None
        if deprecation_date:
            try:
                dep_date = datetime.datetime.strptime(
                    deprecation_date,
                    '%Y%m%d'
                )
                self.deprecation_date = deprecation_date
            except Exception as e:
                msg = 'The deprecation date provided, "%s", is not valid.' \
                    % deprecation_date
                raise EC2DeprecateImgException(msg) from e
        else:
            dep_date = datetime.datetime.now()
            self.deprecation_date = self._format_date(dep_date)

    # ---------------------------------------------------------------------
    def _set_replacement_image_info(self):
        """Find the replacement image information and create an identifier"""
        images = None
        condition = None
        if self.replacement_image_id:
            condition = self.replacement_image_id
            images = self._find_images_by_id(condition)
        elif self.replacement_image_name:
            condition = self.replacement_image_name
            images = self._find_images_by_name(condition)
        elif self.replacement_image_name_fragment:
            condition = self.replacement_image_name_fragment
            images = self._find_images_by_name_fragment(condition)
        elif self.replacement_image_name_match:
            condition = self.replacement_image_name_match
            images = self._find_images_by_name_regex_match(condition)
        else:
            # Set image tag to empty string if no replacement image provided
            self.replacement_image_tag = ''
            return

        if not images:
            msg = 'Replacement image not found, "%s" ' % condition
            msg += 'did not match any image.'
            raise EC2DeprecateImgException(msg)

        if len(images) > 1:
            msg = 'Replacement image ambiguity, the specified condition '
            msg += '"%s" return multiple replacement image options' % condition
            raise EC2DeprecateImgException(msg)

        image = images[0]
        self.replacement_image_tag = '%s -- %s' % (
            image['ImageId'],
            image['Name']
        )

    # ---------------------------------------------------------------------
    def deprecate_images(self):
        """Deprecate images in the connected region"""
        self._connect()
        self._set_replacement_image_info()
        images = self._get_images_to_deprecate()
        if not images:
            self.log.debug('No images to deprecate found')
            return False

        self.log.debug('Deprecating images in region: {}'.format(self.region))
        self.log.debug('\tDeprecated on {}'.format(self.deprecation_date))
        self.log.debug('\tRemoval date {}'.format(self.deletion_date))
        if self.replacement_image_tag:
            self.log.debug(
                '\tReplacement image {}'.format(self.replacement_image_tag)
            )
        else:
            self.log.debug("\tNo replacement image provided")

        ec2 = self._connect()
        for image in images:
            existing_tags = image.get('Tags')
            tagged = False
            if not self.force and existing_tags:
                for tag in existing_tags:
                    if tag.get('Key') == 'Deprecated on':
                        msg = '\t\tImage %s already tagged, skipping'
                        self.log.debug(msg % image['ImageId'])
                        tagged = True
            if tagged:
                continue
            deprecated_on_data = {
                'Key': 'Deprecated on',
                'Value': self.deprecation_date
            }
            removal_date_data = {
                'Key': 'Removal date',
                'Value': self.deletion_date
            }
            tags = [
                deprecated_on_data,
                removal_date_data,
            ]

            if self.replacement_image_tag:
                replacement_image_data = {
                    'Key': 'Replacement image',
                    'Value': self.replacement_image_tag
                }
                tags.append(replacement_image_data)

            ec2.create_tags(
                Resources=[image['ImageId']], Tags=tags
            )
            self.log.debug(
                '\t\ttagged:%s\t%s' % (image['ImageId'], image['Name'])
            )
            # There is a difference in terminology. In EC2 deprecated means
            # an image cannot be used anymore by new users, this is similar
            # to a deletion. For ec2imgutils deprecation means an image should
            # no longer be used. Therefore we set the calculated deletion
            # date as the deprecation date in AWS
            ec2.enable_image_deprecation(
                ImageId=image['ImageId'],
                DeprecateAt=datetime.datetime.strptime(
                    self.deletion_date, '%Y%m%d'
                )
            )

    # ---------------------------------------------------------------------
    def print_deprecation_info(self):
        """Print information about the images that would be deprecated."""
        self._connect()
        self._set_replacement_image_info()
        images = self._get_images_to_deprecate()
        if not images:
            self.log.info('No images to deprecate found')
            return True

        self.log.info(
            'Would deprecate images in region: {}'.format(self.region)
        )
        self.log.info('\tDeprecated on {}'.format(self.deprecation_date))
        self.log.info('\tRemoval date {}'.format(self.deletion_date))
        if self.replacement_image_tag:
            self.log.info(
                '\tReplacement image {}'.format(self.replacement_image_tag)
            )
        else:
            self.log.info("\tNo replacement image provided")

        self.log.info('\tImages to deprecate:\n\t\tID\t\t\t\tName')
        for image in images:
            self.log.info('\t\t%s\t%s' % (image['ImageId'], image['Name']))

        return True
