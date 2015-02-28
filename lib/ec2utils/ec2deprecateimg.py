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
import ConfigParser
import datetime
import dateutil.relativedelta
import re

from ec2utils.ec2DepImgExceptions import *

class EC2DeprecateImg:
    """Deprecate EC2 image(s) by tagging the image with 3 tags, Deprecated on,
       Removal date, and Replacement image."""

    def __init__(self,account,
                 depPeriod=6,
                 config=None,
                 depImgID=None,
                 depImgName=None,
                 depImgNameFrag=None,
                 depImgNameMatch=None,
                 publicOnly=None,
                 region=None,
                 replImgID=None,
                 replImgName=None,
                 replImgNameFrag=None,
                 replImgNameMatch=None,
                 verbose=None,
                 virtType=None):

        self.account    = 'account-' + account
        self.depPeriod  = depPeriod
        self.configFile = config
        self.config     = self._getConfig()

        self._verifyAccount()

        self.accessKey, self.secretKey = self._getAccessKeys()

        self.depImgID         = depImgID
        self.depImgName       = depImgName
        self.depImgNameFrag   = depImgNameFrag
        self.depImgNameMatch  = depImgNameMatch
        self.publicOnly       = publicOnly
        self.region           = region
        self.replImgID        = replImgID
        self.replImgName      = replImgName
        self.replImgNameFrag  = replImgNameFrag
        self.replImgNameMatch = replImgNameMatch
        self.verbose          = verbose

        self.virtType = None
        if virtType:
            if virtType[0:3] == 'par':
                self.virtType = 'paravirtual'
            else:
                self.virtType = 'hvm'
            

        self._setDeprecationDate()
        self._setDeleteDate()
        self.ec2 = None
        if self.region:
            self._connect()
        self.replacementImageID = None
        self.replacementImageTag = None
        if self.ec2:
            self._setReplacementImageInfo()

    #----------------------------------------------------------------------
    def _connect(self):
        """Connect to EC2"""
        if self.ec2:
            return True

        if self.region:
            self.ec2 = boto.ec2.connect_to_region(
                self.region,
                aws_access_key_id=self.accessKey,
                aws_secret_access_key=self.secretKey
            )
        if not self.ec2:
            msg = 'Could not connect to region: %s ' %self.region
            raise EC2DeprecateImgException(msg)

        if self.verbose:
            print 'Connected to region: ', self.region

        self._setReplacementImageInfo()

        return True

    #----------------------------------------------------------------------
    def _disconnect(self):
        """Disconnect from EC2"""
        if self.ec2:
            self.ec2.close()
            self.ec2 = None
            self.replacementImageID = None
            self.replacementImageTag = None

    #----------------------------------------------------------------------
    def _findImagesByID(self, imgID, filterReplImg=None):
        """Find images by ID match"""
        images = []
        myImages = self._getAllTypeMatchImages(filterReplImg)
        for img in myImages:
            if imgID == img.id:
                images.append(img)
                # The framework guarantees unique image IDs
                return images

    #----------------------------------------------------------------------
    def _findImagesByName(self, imgName, filterReplImg=None):
        """Find images by exact name match"""
        images = []
        myImages = self._getAllTypeMatchImages(filterReplImg)
        for img in myImages:
            if not img.name:
                if filterReplImg:
                    msg = 'WARNING: Found image with no name, ignoring for '
                    msg += 'deprecation search. Image ID: %s' %img.id
                    print msg
                continue
            if imgName == img.name:
                images.append(img)

        return images

    #----------------------------------------------------------------------
    def _findImagesByNameFragment(self, nameFragment, filterReplImg=None):
        """Find images by string matching of the fragment with the name"""
        images = []
        myImages = self._getAllTypeMatchImages(filterReplImg)
        for img in myImages:
            if not img.name:
                if filterReplImg:
                    msg = 'WARNING: Found image with no name, ignoring for '
                    msg += 'deprecation search. Image ID: %s' %img.id
                    print msg
                continue
            if img.name.find(nameFragment) != -1:
                images.append(img)

        return images

    #----------------------------------------------------------------------
    def _findImagesByNameRegexMatch(self, expression, filterReplImg=None):
        """Find images by match the name with the given regular expression"""
        images = []
        myImages = self._getAllTypeMatchImages(filterReplImg)
        match = re.compile(expression)
        for img in myImages:
            if not img.name:
                if filterReplImg:
                    msg = 'WARNING: Found image with no name, ignoring for '
                    msg += 'deprecation search. Image ID: %s' %img.id
                    print msg
                continue
            if match.match(img.name):
                images.append(img)

        return images

    #----------------------------------------------------------------------
    def _formatDate(self, date):
        """Format the date to YYYYMMDD"""
        year = date.year
        month = date.month
        day = date.day
        date = '%s' % year
        for item in [month, day]:
            if item > 9:
                date += '%s' %item
            else:
                date += '0%s' %item

        return date

    #----------------------------------------------------------------------
    def _getAccessKeys(self):
        """Get the access keys for the account from the configuration"""
	if not self.config.has_option(self.account, 'access_key_id'):
	    msg = 'No access_key_id option found for %s' %self.account
	    raise EC2DeprecateImgException(msg)
	if not self.config.has_option(self.account, 'secret_access_key'):
	    msg = 'No secret_access_key option found for %s' %self.acount
	    raise EC2DeprecateImgException(msg)

	accessKey = self.config.get(self.account, 'access_key_id')
	secretKey = self.config.get(self.account, 'secret_access_key')

        return accessKey, secretKey
        
    #----------------------------------------------------------------------
    def _getConfig(self):
        """Read the configuration file"""
        config = ConfigParser.RawConfigParser()
        parsed = None
        try:
            parsed = config.read(self.configFile)
        except:
            msg = 'Could not parse configuration file %s' %self.configFile
            type, value, tb = sys.exec_info()
            msg += '\n%s' %value.message
            raise EC2DeprecateImgException(msg)
		
        if not parsed:
            msg = 'Error parsing config file: %s' %self.configFile
            raise EC2DeprecateImgException(msg)

        return config

    #----------------------------------------------------------------------
    def _getAllTypeMatchImages(self, filterReplImg=None):
        """Get all images that match thespecified virtualization type.
           All images owned by the account if not type is specified."""
        images = []
        myImages = self.ec2.get_all_images(owners='self')
        for img in myImages:
            if filterReplImg:
                if img.id == self.replacementImageID:
                    if self.verbose:
                        msg = 'Ignore replacement image as potential target '
                        msg += 'for deprecation.'
                        print msg
                    continue
            if self.virtType:
                if self.virtType == img.virtualization_type:
                    images.append(img)
                else:
                    continue
            if self.publicOnly:
                launchPerm = img.get_launch_permissions().get('groups', None)
                if launchPerm:
                    for item in launchPerm:
                        if item == 'all':
                            images.append(img)
                            break
                continue
            images.append(img)

        return images

    #----------------------------------------------------------------------
    def _getImagesToDeprecate(self):
        """Find images to deprecate"""
        if not self.hasConnection():
            self._connect()
        images = None
        condition = None
        if self.depImgID:
            images = self._findImagesByID(self.depImgID, True)
        elif self.depImgName:
            images = self._findImagesByName(self.depImgName, True)
        elif self.depImgNameFrag:
            images = self._findImagesByNameFragment(self.depImgNameFrag, True)
        elif self.depImgNameMatch:
            images = self._findImagesByNameRegexMatch(
                self.depImgNameMatch, True)
        else:
            msg = 'No deprecation image condition set. Should not reach '
            msg += 'this point.'
            raise EC2DeprecateImgException(msg)

        return images

    #----------------------------------------------------------------------
    def _setDeleteDate(self):
        """Set the date when the deprecation perios expires"""
        now = datetime.datetime.now()
        expire = now + dateutil.relativedelta.relativedelta(
            months=+self.depPeriod)
        self.delDate = self._formatDate(expire)

    #----------------------------------------------------------------------
    def _setDeprecationDate(self):
        """Set the deprecation day in the YYYYMMDD format"""
        now = datetime.datetime.now()
        self.depDate = self._formatDate(now)

    #----------------------------------------------------------------------
    def _setReplacementImageInfo(self):
        """Find the replacement image information and create an identifier"""
        if not self.hasConnection():
            self._connect()
        images = None
        condition = None
        if self.replImgID:
            condition = self.replImgID
            images = self._findImagesByID(condition)
        elif self.replImgName:
            condition = self.replImgName
            images = self._findImagesByName(condition)
        elif self.replImgNameFrag:
            condition = self.replImgNameFrag
            images = self._findImagesByNameFragment(condition)
        elif self.replImgNameMatch:
            condition = self.replImgNameMatch
            images = self._findImagesByNameRegexMatch(condition)
        else:
            msg = 'No replacement image condition set. Should not reach '
            msg += 'this point.'
            raise EC2DeprecateImgException(msg)

        if len(images) > 1:
            msg = 'Replacement image ambiguity, the specified condition '
            msg += '"%s" return multiple replacement image options' %condition
            raise EC2DeprecateImgException(msg)

        img = images[0]
        self.replacementImageID = img.id
        self.replacementImageTag = '%s -- %s' %(img.id, img.name)

    #----------------------------------------------------------------------
    def _verifyAccount(self):
        """Verify that the specified account exists in the configuration"""
        if not self.config.has_section(self.account):
	    msg = 'Could not find account specification for '
            msg += self.account.split('account')[-1][1:]
	    msg += ' in config file '
            msg += self.configFile
	    raise EC2DeprecateImgException(msg)

    #----------------------------------------------------------------------
    def deprecate(self):
        """Deprecate images in the connected region"""
        self._setReplacementImageInfo()
        images = self._getImagesToDeprecate()
        if not images:
            if self.verbose:
                print 'No images to deprecate found'
            return False
        if self.verbose:
            print 'Deprecating images in regin: ', self.region
            print '\tDeprecated on', self.depDate
            print 'Removal date', self.delDate
            print 'Replacement image', self.replacementImageTag
        for img in images:
            img.add_tag('Deprecated on', self.depDate)
            img.add_tag('Removal date', self.delDate)
            img.add_tag('Replacement image', self.replacementImageTag)
            if self.verbose:
                print '\t\ttagged:%s\t%s' %(img.id, img.name)

    #----------------------------------------------------------------------
    def hasConnection(self):
        """Return true if he object is connected to EC2"""
        if self.ec2:
            return True

        return False

    #----------------------------------------------------------------------
    def printDeprecationInfo(self):
        """Print information about the images that would be deprecated."""
        self._setReplacementImageInfo()
        images = self._getImagesToDeprecate()
        if not images:
            print 'No images to deprecate found'
            return True

        print 'Would deprecate images in region: ', self.region
        print '\tDeprecated on', self.depDate
        print '\tRemoval date', self.delDate
        print '\tReplacement image', self.replacementImageTag
        print '\tImages to deprecate:\n\t\tID\t\t\t\tName'
        for img in images:
            print '\t\t%s\t%s' %(img.id, img.name)

        return True
    #----------------------------------------------------------------------
    def setRegion(self, region):
        """Set the regionthat should be used."""
        if self.region and self.region == region:
            return True
        
        self._disconnect()
        self.region = region

        return True

