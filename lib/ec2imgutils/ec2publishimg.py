# Copyright 2020 SUSE LLC
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
# along with ec2publishimg. If not, see <http://www.gnu.org/licenses/>.

import logging

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2PublishImgException


class EC2PublishImage(EC2ImgUtils):
    """Publish/share EC2 image(s). Will also hide the image(s)"""

    # --------------------------------------------------------------------
    def __init__(
            self,
            access_key=None,
            allow_copy='none',
            image_id=None,
            image_name=None,
            image_name_fragment=None,
            image_name_match=None,
            secret_key=None,
            visibility='all',
            log_level=logging.INFO,
            log_callback=None,
            wait_count=1
    ):
        EC2ImgUtils.__init__(
            self,
            log_level=log_level,
            log_callback=log_callback
        )

        self.access_key = access_key
        self.image_id = image_id
        self.image_name = image_name
        self.image_name_fragment = image_name_fragment
        self.image_name_match = image_name_match
        self.secret_key = secret_key
        self.visibility = visibility
        self.wait_count = wait_count

        if self.visibility == 'all':
            self.publish_msg = '\tPublished: %s\t\t%s'
        elif self.visibility == 'none':
            self.publish_msg = '\tSet to private: %s\t\t%s'
        else:
            self.publish_msg = '\tShared: %s\t\t%s\t with: %s'

        if allow_copy == 'image':
            self.allow_copy = self.visibility
        else:
            self.allow_copy = allow_copy

    # --------------------------------------------------------------------
    def _get_images(self):
        """Return a list of images that match the filter criteria"""
        self._connect()
        owned_images = self._get_owned_images()
        if self.image_id:
            return utils.find_images_by_id(owned_images, self.image_id)
        elif self.image_name:
            return utils.find_images_by_name(
                owned_images,
                self.image_name,
                self.log
            )
        elif self.image_name_fragment:
            return utils.find_images_by_name_fragment(
                owned_images,
                self.image_name_fragment,
                self.log
            )
        elif self.image_name_match:
            try:
                return utils.find_images_by_name_regex_match(
                    owned_images,
                    self.image_name_match,
                    self.log
                )
            except Exception:
                msg = 'Unable to complie regular expression "%s"'
                msg = msg % self.image_name_match
                raise EC2PublishImgException(msg)

    # --------------------------------------------------------------------
    def _get_snapshot_ids_for_image(self, image):
        """Return the snapshot ID for a given image"""
        image_data = self._connect().describe_images(
            ImageIds=[image['ImageId']])['Images']
        block_device_maps = image_data[0]['BlockDeviceMappings']
        snapshot_ids = []
        for block_map in block_device_maps:
            snapshot_ids.append(block_map['Ebs']['SnapshotId'])

        return snapshot_ids

    # --------------------------------------------------------------------
    def _share_snapshot(self, image):
        """Provide permission to copy the underlying snapshot"""

        snapshot_ids = self._get_snapshot_ids_for_image(image)
        for snapshot_id in snapshot_ids:
            if self.allow_copy == 'all':
                self._connect().modify_snapshot_attribute(
                    SnapshotId=snapshot_id,
                    Attribute='createVolumePermission',
                    OperationType='add',
                    GroupNames=['all']
                )
            elif self.allow_copy != 'none':
                self._connect().modify_snapshot_attribute(
                    SnapshotId=snapshot_id,
                    Attribute='createVolumePermission',
                    OperationType='add',
                    UserIds=self.allow_copy.split(',')
                )

    # --------------------------------------------------------------------
    def _print_image_info(self, image, log_callback):
        """Print a message about the image that would be modified"""
        if self.visibility == 'all' or self.visibility == 'none':
            log_callback(
                self.publish_msg % (image['ImageId'], image['Name'])
            )
        else:
            log_callback(self.publish_msg % (
                        image['ImageId'],
                        image['Name'],
                        self.visibility
            ))

    # --------------------------------------------------------------------
    def print_publish_info(self):
        """Print information about images that would be published"""
        images = self._get_images()
        for image in images:
            self._print_image_info(image, log_callback=self.log.info)

    # --------------------------------------------------------------------
    def publish_images(self):
        """Publish the matching image(s)"""
        images = self._get_images()

        for image in images:
            if image['State'] != 'available':
                waiter = self._connect().get_waiter('image_available')
                loop_count = 0
                while loop_count < self.wait_count:
                    self.log.info('Current state of image %s is %s. \
                                  Waiting up to 10 minutes for it to \
                                  become available.',
                                  image['ImageId'], image['State'])
                    try:
                        wait_status = waiter.wait(
                            ImageIds=[image['ImageId']],
                            Filters=[
                                {
                                    'Name': 'state',
                                    'Values': ['available']
                                }
                            ]
                        )
                    except Exception:
                        self.log.error('Skipping image %s as the image state \
                                       could not be checked',
                                       image['ImageId'])
                        continue

                    if wait_status:
                        if loop_count == self.wait_count:
                            self.log.info("Skipping image %s as it failed to \
                                          become 'available",
                                          image['ImageId'])
                            continue
                        else:
                            loop_count += 1
                            self.log.info("Image %s is still not 'available'.",
                                          image['ImageId'])
                            self.log.info('Entering wait loop number %d of %d',
                                          loop_count, self.wait_count)
                    else:
                        loop_count = self.wait_count
                        self.log.info("Image %s is now 'available'.",
                                      image['ImageId'])

            if self.visibility == 'all':
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission',
                    OperationType='add',
                    UserGroups=['all']
                )
                if self.allow_copy != 'none':
                    self._share_snapshot(image)
            elif self.visibility == 'none':
                launch_attributes = self._connect().describe_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission'
                )['LaunchPermissions']
                launch_permission = {
                    'Remove': launch_attributes
                }
                if not launch_attributes:
                    msg = '\tImage with ID: %s  ' % image['ImageId']
                    msg += 'is already private, nothing to do'
                    self.log.info(msg)
                    continue
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    LaunchPermission=launch_permission
                )
                snapshot_ids = self._get_snapshot_ids_for_image(image)
                for snapshot_id in snapshot_ids:
                    snapshot_attrs = (
                        self._connect().describe_snapshot_attribute(
                            SnapshotId=snapshot_id,
                            Attribute='createVolumePermission'
                        )['CreateVolumePermissions']
                    )
                    if not snapshot_attrs:
                        continue
                    snapshot_permission = {
                        'Remove': snapshot_attrs
                    }
                    self._connect().modify_snapshot_attribute(
                        SnapshotId=snapshot_id,
                        CreateVolumePermission=snapshot_permission
                    )
            else:
                self._connect().modify_image_attribute(
                    ImageId=image['ImageId'],
                    Attribute='launchPermission',
                    OperationType='add',
                    UserIds=self.visibility.split(',')
                )
                if self.allow_copy:
                    self._share_snapshot(image)

            self._print_image_info(image, log_callback=self.log.debug)
