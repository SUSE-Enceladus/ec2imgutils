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
# along with ec2imgutils.  If not, see <http://www.gnu.org/licenses/>.


class EC2AccountException(Exception):
    pass


class EC2ConfigFileParseException(Exception):
    pass


class EC2ConnectionException(Exception):
    pass


class EC2DeprecateImgException(Exception):
    pass


class EC2PublishImgException(Exception):
    pass


class EC2RemoveImgException(Exception):
    pass


class EC2UploadImgException(Exception):
    pass
