# Copyright 2015 SUSE LLC, Robert Schweikert
#
# This file is part of ec2deprecateimg.
# ec2deprecateimg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# ec2deprecateimg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with ec2deprecateimg. If not, see <http://www.gnu.org/licenses/>.

import boto
import boto.ec2

class EC2DeprecateImg:
    """Deprecate EC2 image(s) by tagging the image with 3 tags, Deprecated on,
       Removal date, and Replacement image."""

    def __init__(self):
        pass

#for region in regions:
#    print 'Region: %s ' %region
#    ec2 = boto.ec2.connect_to_region(
#        region,
#        aws_access_key_id=accessKey,
#        aws_secret_access_key=secretKey
#    )
#    images = ec2.get_all_images(owners='self')
#    found = None
#    # Find the image ID of the latest image, this is always the replacement
#    # image
#    replImgID = None
#    osVer = None
#    for img in images:
#       if img.name and img.name.find(options.match.strip()) != -1:
#           replImgID = img.id
#           imgNamePrts = img.name.split('-')
#    for img in images:
#       if img.id == replImgID:
#           continue
#       # Special case skip sles 12 for now
#       elif img.name.find('sles-12') != -1:
#           continue
#       else:
#           imgAttr = ec2.get_image_attribute(img.id,
#                                             attribute='launchPermission')
#           if imgAttr.attrs and imgAttr.attrs.has_key('groups'):
#               launchPerm = imgAttr.attrs['groups']
#               if launchPerm == 'all':
#                   img.add_tag('Deprecated on', deprecationDate)
#                   img.add_tag('Removal date', deletionDate)
#                   img.add_tag('Replacement image', replImgID)
#
#if not found:
#    print 'No images found the match specified name: ', options.match
