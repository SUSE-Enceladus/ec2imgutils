# Copyright 2018 SUSE LLC
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
import time

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2RemoveImgException


class EC2RemoveImage(EC2ImgUtils):
    """Remove images from EC2."""

    # --------------------------------------------------------------------
    def __init__(
            self,
            access_key=None,
            image_id=None,
            image_name=None,
            image_name_fragment=None,
            image_name_match=None,
            keep_snap=False,
            no_confirm=None,
            remove_all=False,
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
        self.image_name_fragment = image_name_fragment
        self.image_name_match = image_name_match
        self.keep_snap = keep_snap
        self.no_confirm = no_confirm
        self.remove_all = remove_all
        self.secret_key = secret_key

    # ---------------------------------------------------------------------
    def _check_images_boundary_condition(self, images):
        """Check if the images found meet operating conditions:
           If all is true we delete all found images if not we should have
           found only one image"""

        if not images:
            self.log.info('No images to remove found in region', self.region)

        if len(images) > 1 and not self.remove_all:
            msg = 'Found multiple images to remove, but "all" is '
            msg += 'not set. Cannot disambiguate images to remove'
            self.log.info(msg)
            return False

        return True

    # ---------------------------------------------------------------------
    def _get_images_to_remove(self):
        """Find the images to remove"""
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
                raise EC2RemoveImgException(msg)
        else:
            msg = 'No deprecation image condition set. Should not reach '
            msg += 'this point.'
            raise EC2RemoveImgException(msg)

    # ---------------------------------------------------------------------
    def _get_snapshot_id(self, image):
        """Get the snapshot id associated with this image"""
        device_map = image.get('BlockDeviceMappings')
        if not device_map:
            error_msg = 'Image "%s" has no device map' % image.get('Name')
            raise EC2RemoveImgException(error_msg)
        # The image snapshot should be the first device
        ebs_info = device_map[0].get('Ebs')
        if not ebs_info:
            error_msg = 'Image "%s" is not EBS backed' % image.get('Name')
            raise EC2RemoveImgException(error_msg)
        snapshot_id = ebs_info.get('SnapshotId')
        if not snapshot_id:
            error_msg = 'No snapshot found for image "%s"' % image.get('Name')
            raise EC2RemoveImgException(error_msg)
        return snapshot_id

    # ---------------------------------------------------------------------
    def print_remove_info(self):
        """Print information about images that would be deleted"""
        images = self._get_images_to_remove()
        images_ok = self._check_images_boundary_condition(images)

        if not images_ok:
            # While the boundary conditions are not met, we are just printing
            # information thus this is not considered a failure
            return True

        header_msg = 'Would remove image '
        if not self.keep_snap:
            header_msg += 'and snapshot '
        header_msg += 'in region: '
        self.log.info(header_msg, self.region)
        for image in images:
            if not self.keep_snap:
                snapshot = self._get_snapshot_id(image)
                self.log.info('\t\t%s\t%s\t%s' % (
                    image['ImageId'],
                    image['Name'],
                    snapshot
                ))
            else:
                self.log.info('\t\t%s\t%s' % (image['ImageId'], image['Name']))

        return True

    # ---------------------------------------------------------------------
    def remove_images(self):
        """Remove the images"""
        ec2 = self._connect()
        images = self._get_images_to_remove()
        images_ok = self._check_images_boundary_condition(images)

        if not images_ok:
            raise EC2RemoveImgException('Image ambiguity')

        for image in images:
            ec2.deregister_image(ImageId=image['ImageId'])
            if not self.keep_snap:
                snapshot = self._get_snapshot_id(image)
                # Give the EC2 backend a little bit of time to catch up
                time.sleep(1)
                ec2.delete_snapshot(SnapshotId=snapshot)

            self.log.debug('Removing in region: {}'.format(self.region))
            self.log.debug(
                '\tImage: %s\t%s' % (image['ImageId'], image['Name'])
            )
            if not self.keep_snap:
                self.log.debug('\tSnapshot: {}'.format(snapshot))
