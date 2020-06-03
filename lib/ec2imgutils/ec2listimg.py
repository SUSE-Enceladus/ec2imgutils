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

import pprint

import ec2imgutils.ec2utils as utils
from ec2imgutils.ec2imgutils import EC2ImgUtils
from ec2imgutils.ec2imgutilsExceptions import EC2ListImgException


class EC2ListImage(EC2ImgUtils):
    """List image in account."""

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
            verbose=None):
        EC2ImgUtils.__init__(self)

        self.access_key = access_key
        self.indent = indent
        self.image_id = image_id
        self.image_name = image_name
        self.image_name_fragment = image_name_fragment
        self.image_name_match = image_name_match
        self.secret_key = secret_key
        self.verbose = verbose

    # ---------------------------------------------------------------------
    def _get_images_to_list(self):
        """Find the images to list"""
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
            except Exception:
                msg = 'Unable to complie regular expression "%s"'
                msg = msg % self.image_name_match
                raise EC2ListImgException(msg)
        else:
            return owned_images

    # ---------------------------------------------------------------------
    def list_images(self):
        """List th eimages that match in the accoount"""
        self._connect()
        images = self._get_images_to_list()

        for image in images:
            output = ' ' * self.indent
            if self.verbose == 0:
                print(output + image.get('Name'))
            elif self.verbose == 1:
                print(output + image.get('Name') + '\t' + image.get('ImageId'))
            else:
                pp = pprint.PrettyPrinter(indent=(4 + self.indent))
                pp.pprint(image)

    # ---------------------------------------------------------------------
    def set_intent(self, indent):
        """Set the indent level for the output"""
        self.indent = indent
