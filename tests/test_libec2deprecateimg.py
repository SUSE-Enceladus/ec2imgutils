#!/usr/bin/python3
#
# Copyright (c) 2015 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of ec2utils
#
# ec2utils is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# ec2utils is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2utils. If not, see
# <http://www.gnu.org/licenses/>.
#

import logging
import pytest
import datetime
import dateutil.relativedelta

from unittest.mock import patch, MagicMock

import ec2imgutils.ec2deprecateimg as ec2depimg

from ec2imgutils.ec2imgutilsExceptions import (
    EC2DeprecateImgException
)

logger = logging.getLogger('ec2imgutils')
logger.setLevel(logging.INFO)
# --------------------------------------------------------------------
# Test data for deprecation date parameter
today = datetime.datetime.now()
today_tag = today.strftime('%Y%m%d')
one_month_delta = dateutil.relativedelta.relativedelta(months=+1)
six_month_delta = dateutil.relativedelta.relativedelta(months=+6)

test_depr_date_data = [
    ("", 1, False, today_tag, (today + one_month_delta).strftime('%Y%m%d')),
    ("", 6, False, today_tag, (today + six_month_delta).strftime('%Y%m%d')),
    ("20220707", 6, False, '20220707', '20230107'),
    ("20221231", 1, False, '20221231', '20230131'),
    ("20220331", 1, False, '20220331', '20220430'),
    ("asdf", 6, True, '', ''),
    ("20220230", 6, True, '', ''),
    ("2022", 6, True, '', ''),
]


@pytest.mark.parametrize(
    "depr_date,depr_period,expected_exc,expected_depr_date,expected_del_date",
    test_depr_date_data
)
def test_deprecation_date_parameter(
    depr_date,
    depr_period,
    expected_exc,
    expected_depr_date,
    expected_del_date
):
    """Test deprecation_date parameter"""
    if expected_exc:
        with pytest.raises(EC2DeprecateImgException) as depr_exc:
            deprecator = ec2depimg.EC2DeprecateImg(
                access_key='',
                deprecation_date=depr_date,
                deprecation_period=depr_period,
                deprecation_image_id='',
                deprecation_image_name='',
                deprecation_image_name_fragment='',
                deprecation_image_name_match='',
                force=False,
                image_virt_type='',
                public_only=False,
                replacement_image_id='',
                replacement_image_name='',
                replacement_image_name_fragment='',
                replacement_image_name_match='',
                secret_key='',
                log_callback=logger
            )
        assert "deprecation date" in str(depr_exc.value)
        assert depr_date in str(depr_exc.value)

    else:
        deprecator = ec2depimg.EC2DeprecateImg(
            access_key='',
            deprecation_date=depr_date,
            deprecation_period=depr_period,
            deprecation_image_id='',
            deprecation_image_name='',
            deprecation_image_name_fragment='',
            deprecation_image_name_match='',
            force=False,
            image_virt_type='',
            public_only=False,
            replacement_image_id='',
            replacement_image_name='',
            replacement_image_name_fragment='',
            replacement_image_name_match='',
            secret_key='',
            log_callback=logger
        )
        assert expected_depr_date == deprecator.deprecation_date
        assert expected_del_date == deprecator.deletion_date


# -----------------------------------------------------------------------------
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._get_owned_images')
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._connect')
def test_deprecate_class_filtering_by_name_match_no_virt_type_no_pub_img(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))

    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    deprecator = ec2depimg.EC2DeprecateImg(
        access_key='',
        deprecation_date='20220101',
        deprecation_period=6,
        deprecation_image_id='',
        deprecation_image_name='',
        deprecation_image_name_fragment='est',
        deprecation_image_name_match='',
        force=False,
        image_virt_type='',
        public_only=False,
        replacement_image_id='',
        replacement_image_name='',
        replacement_image_name_fragment='',
        replacement_image_name_match='',
        secret_key='',
        log_callback=logger
    )
    images = deprecator._get_images_to_deprecate()
    assert 3 == len(images)


@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._get_owned_images')
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._connect')
def test_deprecate_class_filtering_by_name_match_virt_type_no_pub_img(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))

    ec2 = MagicMock()
    ec2.create_tags.return_value = None
    ec2.create_tags.side_effect = log_args
    ec2.enable_image_deprecation.return_value = None
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    deprecator = ec2depimg.EC2DeprecateImg(
        access_key='',
        deprecation_date='20220101',
        deprecation_period=6,
        deprecation_image_id='',
        deprecation_image_name='',
        deprecation_image_name_fragment='est',
        deprecation_image_name_match='',
        force=False,
        image_virt_type='hvm',
        public_only=False,
        replacement_image_id='',
        replacement_image_name='',
        replacement_image_name_fragment='',
        replacement_image_name_match='',
        secret_key='',
        log_callback=logger
    )
    images = deprecator._get_images_to_deprecate()
    assert 1 == len(images)
    assert "ami-000cc31892067693a" == images[0]['ImageId']


@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._get_owned_images')
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._connect')
def test_deprecate_class_filtering_by_name_match_no_virt_type_pub_img(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))

    la1 = {}
    launchAtt1 = MagicMock()
    launchAtt1.get.return_value = 'all'
    la1['LaunchPermissions'] = [launchAtt1]

    la2 = {}
    launchAtt2 = MagicMock()
    launchAtt2.get.return_value = 'all'
    la2['LaunchPermissions'] = [launchAtt1]

    ec2 = MagicMock()
    ec2.describe_image_attribute.side_effect = [la1, la2, la2]
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    deprecator = ec2depimg.EC2DeprecateImg(
        access_key='',
        deprecation_date='20220101',
        deprecation_period=6,
        deprecation_image_id='',
        deprecation_image_name='',
        deprecation_image_name_fragment='est',
        deprecation_image_name_match='',
        force=False,
        image_virt_type='',
        public_only=True,
        replacement_image_id='',
        replacement_image_name='',
        replacement_image_name_fragment='',
        replacement_image_name_match='',
        secret_key='',
        log_callback=logger
    )
    images = deprecator._get_images_to_deprecate()
    assert 3 == len(images)


@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._get_owned_images')
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._connect')
def test_deprecate_class_filtering_by_name_match_no_virt_type_pub_img2(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))

    la1 = {}
    launchAtt1 = MagicMock()
    launchAtt1.get.return_value = 'all'
    la1['LaunchPermissions'] = [launchAtt1]

    la2 = {}
    launchAtt2 = MagicMock()
    launchAtt2.get.return_value = 'NOTall'
    la2['LaunchPermissions'] = [launchAtt2]

    ec2 = MagicMock()
    ec2.describe_image_attribute.side_effect = [la1, la2, la2]
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    deprecator = ec2depimg.EC2DeprecateImg(
        access_key='',
        deprecation_date='20220101',
        deprecation_period=6,
        deprecation_image_id='',
        deprecation_image_name='',
        deprecation_image_name_fragment='est',
        deprecation_image_name_match='',
        force=False,
        image_virt_type='',
        public_only=True,
        replacement_image_id='',
        replacement_image_name='',
        replacement_image_name_fragment='',
        replacement_image_name_match='',
        secret_key='',
        log_callback=logger
    )
    images = deprecator._get_images_to_deprecate()
    assert 1 == len(images)
    assert "ami-000cc31892067693a" == images[0]['ImageId']


@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._get_owned_images')
@patch('ec2imgutils.ec2deprecateimg.EC2DeprecateImg._connect')
def test_deprecate_class_filtering_by_name_match_virt_type_pub_img(
    ec2connect_mock,
    get_owned_imgs_mock,
    caplog
):
    def log_args(**kwargs):
        logger.info(str(kwargs))

    la1 = {}
    launchAtt1 = MagicMock()
    launchAtt1.get.return_value = 'all'
    la1['LaunchPermissions'] = [launchAtt1]

    la2 = {}
    launchAtt2 = MagicMock()
    launchAtt2.get.return_value = 'NOTall'
    la2['LaunchPermissions'] = [launchAtt2]

    ec2 = MagicMock()
    ec2.describe_image_attribute.side_effect = [la2, la1]
    ec2connect_mock.return_value = ec2
    get_owned_imgs_mock.return_value = mock_get_owned_images()

    deprecator = ec2depimg.EC2DeprecateImg(
        access_key='',
        deprecation_date='20220101',
        deprecation_period=6,
        deprecation_image_id='',
        deprecation_image_name='',
        deprecation_image_name_fragment='est',
        deprecation_image_name_match='',
        force=False,
        image_virt_type='para',
        public_only=True,
        replacement_image_id='',
        replacement_image_name='',
        replacement_image_name_fragment='',
        replacement_image_name_match='',
        secret_key='',
        log_callback=logger
    )
    images = deprecator._get_images_to_deprecate()
    assert 1 == len(images)
    assert "ami-000cc31892067693c" == images[0]['ImageId']


# --------------------------------------------------------------------
# Aux functions
def mock_get_owned_images():
    myImage1 = {}
    myImage1["Architecture"] = "x86_64"
    myImage1["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage1["ImageId"] = "ami-000cc31892067693a"
    myImage1["Name"] = "testImageName"
    myI1Ebs = {}
    myI1Ebs["DeleteOnTermination"] = True
    myI1Ebs["SnapshotId"] = "snap-000f48a8fa4545e1a"
    myI1Ebs["VolumeSize"] = 10
    myI1Ebs["VolumeType"] = "gp3"
    myI1Ebs["Encrypted"] = False
    bdmI1 = {}
    bdmI1["DeviceName"] = "/dev/sda1"
    bdmI1["Ebs"] = myI1Ebs
    myImage1["BlockDeviceMappings"] = []
    myImage1["BlockDeviceMappings"].append(bdmI1)
    myImage1["VirtualizationType"] = "hvm"

    myImage2 = {}
    myImage2["Architecture"] = "x86_64"
    myImage2["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage2["ImageId"] = "ami-000cc31892067693b"
    myImage2["Name"] = "NotTestImage"
    myI2Ebs = {}
    myI2Ebs["DeleteOnTermination"] = True
    myI2Ebs["SnapshotId"] = "snap-000f48a8fa4545e1b"
    myI2Ebs["VolumeSize"] = 10
    myI2Ebs["VolumeType"] = "gp3"
    myI2Ebs["Encrypted"] = False
    bdmI2 = {}
    bdmI2["DeviceName"] = "/dev/sda1"
    bdmI2["Ebs"] = myI2Ebs
    myImage2["BlockDeviceMappings"] = []
    myImage2["BlockDeviceMappings"].append(bdmI2)
    myImage2["VirtualizationType"] = "para"

    myImage3 = {}
    myImage3["Architecture"] = "x86_64"
    myImage3["CreationDate"] = "2022-04-11T14:01:58.000Z"
    myImage3["ImageId"] = "ami-000cc31892067693c"
    myImage3["Name"] = "testImageName2"
    myI3Ebs = {}
    myI3Ebs["DeleteOnTermination"] = True
    myI3Ebs["SnapshotId"] = "snap-000f48a8fa4545e1a"
    myI3Ebs["VolumeSize"] = 10
    myI3Ebs["VolumeType"] = "gp3"
    myI3Ebs["Encrypted"] = False
    bdmI3 = {}
    bdmI3["DeviceName"] = "/dev/sda1"
    bdmI3["Ebs"] = myI1Ebs
    myImage3["BlockDeviceMappings"] = []
    myImage3["BlockDeviceMappings"].append(bdmI1)
    myImage3["VirtualizationType"] = "para"
    myImages = []
    myImages.append(myImage1)
    myImages.append(myImage2)
    myImages.append(myImage3)
    return myImages
