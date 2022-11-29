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
# along with ec2pub

import logging
import pprint

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2ListImgException


class EC2ListImage(EC2ImgUtils):
    """List owned images in an account."""

    # --------------------------------------------------------------------
    def __init__(
            self,
            access_key=None,
            image_id=None,
            image_name=None,
            image_name_fragment=None,
            image_name_match=None,
            indent=0,
            secret_key=None,
            log_level=logging.INFO,
            log_callback=None,
            verbose=0,
            ec2_client=None
    ):
        EC2ImgUtils.__init__(
            self,
            log_level=log_level,
            log_callback=log_callback,
            ec2_client=ec2_client
        )

        self.access_key = access_key
        self.indent = indent
        self.image_id = image_id
        self.image_name = image_name
        self.image_name_fragment = image_name_fragment
        self.image_name_match = image_name_match
        self.secret_key = secret_key
        self.verbose = verbose

    # ---------------------------------------------------------------------
    def list_images(self):
        """List images that meet the criteria"""
        owned_images = self._get_owned_images()
        if self.image_id:
            return utils.find_images_by_id(
                owned_images, self.image_id
            )
        elif self.image_name:
            return utils.find_images_by_name(
                owned_images, self.image_name, self.log
            )
        elif self.image_name_fragment:
            return utils.find_images_by_name_fragment(
                owned_images, self.image_name_fragment, self.log
            )
        elif self.image_name_match:
            try:
                return utils.find_images_by_name_regex_match(
                    owned_images, self.image_name_match, self.log
                )
            except Exception:
                msg = 'Unable to complie regular expression "%s"'
                msg = msg % self.image_name_match
                raise EC2ListImgException(msg)
        else:
            return owned_images

    # ---------------------------------------------------------------------
    def output_image_list(self):
        """Output the images that match in the account"""
        self._connect()
        images = self.list_images()

        for image in images:
            output = ' ' * self.indent
            if self.verbose == 0:
                self.log.info(output + image.get('Name'))
            elif self.verbose == 1:
                self.log.info(
                    output + image.get('Name') + '\t' + image.get('ImageId')
                )
            else:
                pp = pprint.PrettyPrinter(indent=(4 + self.indent))
                self.log.info(pp.pformat(image))
                if len(images) > 1 and image != images[-1]:
                    self.log.info('')

    # ---------------------------------------------------------------------
    def set_indent(self, indent):
        """Set the indent level for the output"""
        self.indent = indent
