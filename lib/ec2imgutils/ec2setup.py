# Copyright (c) 2018 SUSE LLC
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

import os
import random
import datetime

from ec2imgutils.ec2imgutils import EC2ImgUtils
from tempfile import mkstemp
from tempfile import mkdtemp


class EC2Setup(EC2ImgUtils):
    """Class to prepare an Amazon EC2 account with all necessary resources"""

    def __init__(self, access_key, region, secret_key, session_token, verbose):
        EC2ImgUtils.__init__(self)
        self.access_key = access_key
        self.region = region
        self.secret_key = secret_key
        self.session_token = session_token
        self.verbose = verbose

        self.internet_gateway_id = ''
        self.key_pair_name = ''
        self.route_table_id = ''
        self.security_group_id = ''
        self.ssh_private_key_file = ''
        self.temp_dir = ''
        self.vpc_subnet_id = ''
        self.vpc_id = ''

    # ---------------------------------------------------------------------
    def clean_up(self):
        if self.key_pair_name:
            self._remove_upload_key_pair()
        if self.security_group_id:
            self._remove_security_group()
        if self.vpc_id:
            self._remove_vpc()

    # ---------------------------------------------------------------------
    def create_security_group(self, vpc_id=None):
        if self.verbose:
            print('Creating temporary security group')
        group_name = ''
        # Avoid name collisions
        while not group_name:
            group_name = 'ec2uploadimg-%s' % (random.randint(1, 100))
            groups = self._connect().describe_security_groups()
            for group in groups['SecurityGroups']:
                if group_name == group.get('GroupName'):
                    group_name = ''
                    break
        group_description = 'ec2uploadimg created %s' % datetime.datetime.now()
        if not vpc_id:
            vpc_id = self.vpc_id
        response = self._connect().create_security_group(
            GroupName=group_name, Description=group_description,
            VpcId=vpc_id
        )

        self.security_group_id = response['GroupId']
        if self.verbose:
            print('Temporary Security Group Created %s in vpc %s'
                  % (self.security_group_id, vpc_id))
        self._connect().authorize_security_group_ingress(
            GroupId=self.security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])

        if self.verbose:
            print("Successfully allowed incoming SSH port 22 for security "
                  "group %s in %s" % (self.security_group_id, self.vpc_id))
        return self.security_group_id

    # ---------------------------------------------------------------------
    def create_upload_key_pair(self, key_name='temporary_ec2_uploadkey'):
        if self.verbose:
            print('Creating temporary key pair')
        dir_path = os.path.expanduser('~/')
        if not os.access(dir_path, os.W_OK):
            dir_path = mkdtemp()
            self.temp_dir = dir_path
        fd, location = mkstemp(prefix='temporary_ec2_uploadkey.',
                               suffix='.key', dir=dir_path)
        self.key_pair_name = os.path.basename(location)
        self.ssh_private_key_file = location
        secret_key_content = self._connect().create_key_pair(
            KeyName=self.key_pair_name
        )
        if self.verbose:
            print('Successfully created key pair: ', self.key_pair_name)
        with open(location, 'w') as localfile:
            localfile.write(secret_key_content['KeyMaterial'])
        if self.verbose:
            print('Successfully wrote secret key key file to ', location)
        os.close(fd)
        return self.key_pair_name, self.ssh_private_key_file

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
        if self.verbose:
            print("Successfully created internet gateway %s" %
                  self.internet_gateway_id)

    # ---------------------------------------------------------------------
    def _create_route_table(self):
        response = self._connect().create_route_table(VpcId=self.vpc_id)
        self.route_table_id = response['RouteTable']['RouteTableId']
        self._connect().create_route(
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=self.internet_gateway_id,
            RouteTableId=self.route_table_id
        )
        if self.verbose:
            print("Successfully created route table %s" % self.route_table_id)

    # ---------------------------------------------------------------------
    def _create_vpc(self):
        vpc_name = 'uploader-%s' % (random.randint(1, 100))
        response = self._connect().create_vpc(CidrBlock='192.168.0.0/16')
        self.vpc_id = response['Vpc']['VpcId']
        self._connect().create_tags(
            Resources=[self.vpc_id],
            Tags=[{'Key': 'Name', 'Value': vpc_name}]
        )
        if self.verbose:
            print("Successfully created VPC with id %s" % (self.vpc_id))

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
        if self.verbose:
            print("Successfully created VPC subnet with id %s" %
                  self.vpc_subnet_id)

    # ---------------------------------------------------------------------
    def _remove_security_group(self):
        self._connect().delete_security_group(
            GroupId=self.security_group_id
        )
        if self.verbose:
            print('Successfully deleted security group %s' %
                  self.security_group_id)

    # ---------------------------------------------------------------------
    def _remove_upload_key_pair(self):
        if self.verbose:
            print('Deleting temporary key pair ', self.key_pair_name)
        self._connect().delete_key_pair(
            KeyName=self.key_pair_name)
        if os.path.isfile(self.ssh_private_key_file):
            os.remove(self.ssh_private_key_file)
        if self.temp_dir:
            os.rmdir(self.temp_dir)
        if self.verbose:
            print('Successfully deleted temporary key',
                  self.ssh_private_key_file)

    # ---------------------------------------------------------------------
    def _remove_vpc(self):
        self._connect().delete_route(
            DestinationCidrBlock='0.0.0.0/0', RouteTableId=self.route_table_id
        )
        if self.verbose:
            print('Successfully deleted route from route table %s' %
                  self.route_table_id)
        self._connect().delete_subnet(SubnetId=self.vpc_subnet_id)
        if self.verbose:
            print('Successfully deleted VPC subnet %s' % self.vpc_subnet_id)
        self._connect().delete_route_table(RouteTableId=self.route_table_id)
        if self.verbose:
            print('Successfully deleted route table %s' % self.route_table_id)
        self._connect().detach_internet_gateway(
            InternetGatewayId=self.internet_gateway_id, VpcId=self.vpc_id
        )
        if self.verbose:
            print('Successfully deleted detached internet gateway %s' %
                  self.internet_gateway_id)
        self._connect().delete_internet_gateway(
            InternetGatewayId=self.internet_gateway_id
        )
        if self.verbose:
            print('Successfully deleted internet gateway %s' %
                  self.internet_gateway_id)
        self._connect().delete_vpc(VpcId=self.vpc_id)
        if self.verbose:
            print('Successfully deleted VPC %s' % self.vpc_id)
