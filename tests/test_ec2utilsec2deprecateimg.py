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
