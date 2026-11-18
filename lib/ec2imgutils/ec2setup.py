# Copyright (c) 2019 SUSE LLC
#
# This file is part of ec2imgutils.
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
# along with ec2imgutils.ase.  If not, see <http://www.gnu.org/licenses/>.

import logging
import random

from ec2imgutils.ec2imgutils import EC2ImgUtils


class EC2Setup(EC2ImgUtils):
    """Class to prepare an Amazon EC2 account with all necessary resources"""

    def __init__(
            self,
            access_key,
            region,
            secret_key,
            session_token,
            log_level=logging.INFO,
            log_callback=None
    ):
        EC2ImgUtils.__init__(
            self,
            log_level=log_level,
            log_callback=log_callback
        )

        self.access_key = access_key
        self.region = region
        self.secret_key = secret_key
        self.session_token = session_token

        self.internet_gateway_id = ''
        self.route_table_id = ''
        self.vpc_subnet_id = ''
        self.vpc_id = ''

    # ---------------------------------------------------------------------
    def clean_up(self):
        if self.vpc_id:
            self._remove_vpc()

    # ---------------------------------------------------------------------
    def create_vpc_subnet(self):
        self._create_vpc()
        self._create_internet_gateway()
        self._create_route_table()
        self._create_vpc_subnet()
        return self.vpc_subnet_id

    # ---------------------------------------------------------------------
    def _create_internet_gateway(self):
        response = self._connect().create_internet_gateway()
        self.internet_gateway_id = \
            response['InternetGateway']['InternetGatewayId']
        self._connect().attach_internet_gateway(
            VpcId=self.vpc_id, InternetGatewayId=self.internet_gateway_id
        )
        self.log.debug(
            "Successfully created internet gateway %s"
            % self.internet_gateway_id
        )

    # ---------------------------------------------------------------------
    def _create_route_table(self):
        response = self._connect().create_route_table(VpcId=self.vpc_id)
        self.route_table_id = response['RouteTable']['RouteTableId']
        self._connect().create_route(
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=self.internet_gateway_id,
            RouteTableId=self.route_table_id
        )
        self.log.debug(
            "Successfully created route table %s" % self.route_table_id
        )

    # ---------------------------------------------------------------------
    def _create_vpc(self):
        vpc_name = 'uploader-%s' % (random.randint(1, 100))
        response = self._connect().create_vpc(CidrBlock='192.168.0.0/16')
        self.vpc_id = response['Vpc']['VpcId']
        self._connect().create_tags(
            Resources=[self.vpc_id],
            Tags=[{'Key': 'Name', 'Value': vpc_name}]
        )
        self.log.debug("Successfully created VPC with id %s" % self.vpc_id)

    # ---------------------------------------------------------------------
    def _create_vpc_subnet(self):
        response = self._connect().create_subnet(
            CidrBlock='192.168.1.0/24', VpcId=self.vpc_id
        )
        self.vpc_subnet_id = response['Subnet']['SubnetId']
        self._connect().associate_route_table(
            SubnetId=self.vpc_subnet_id, RouteTableId=self.route_table_id
        )
        self._connect().modify_subnet_attribute(
            MapPublicIpOnLaunch={'Value': True}, SubnetId=self.vpc_subnet_id
        )
        self.log.debug(
            "Successfully created VPC subnet with id %s" % self.vpc_subnet_id
        )

    # ---------------------------------------------------------------------
    def _remove_vpc(self):
        self._connect().delete_route(
            DestinationCidrBlock='0.0.0.0/0', RouteTableId=self.route_table_id
        )
        self.log.debug(
            'Successfully deleted route from route table %s'
            % self.route_table_id
        )
        self._connect().delete_subnet(SubnetId=self.vpc_subnet_id)
        self.log.debug(
            'Successfully deleted VPC subnet %s' % self.vpc_subnet_id
        )
        self._connect().delete_route_table(RouteTableId=self.route_table_id)
        self.log.debug(
            'Successfully deleted route table %s' % self.route_table_id
        )
        self._connect().detach_internet_gateway(
            InternetGatewayId=self.internet_gateway_id, VpcId=self.vpc_id
        )
        self.log.debug(
            'Successfully deleted detached internet gateway %s'
            % self.internet_gateway_id
        )
        self._connect().delete_internet_gateway(
            InternetGatewayId=self.internet_gateway_id
        )
        self.log.debug(
            'Successfully deleted internet gateway %s'
            % self.internet_gateway_id
        )
        self._connect().delete_vpc(VpcId=self.vpc_id)
        self.log.debug('Successfully deleted VPC %s' % self.vpc_id)
