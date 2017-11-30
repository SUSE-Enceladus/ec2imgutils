#!/usr/bin/env python
"""Setup module for ec2utilsbase"""

# Copyright (c) 2017 SUSE LLC
#
# This file is part of ec2utilsbase.
#
# ec2utilsbase is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ec2utilsbase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ec2utilsbase. If not, see <http://www.gnu.org/licenses/>.

import sys

try:
    import setuptools
except ImportError:
    sys.stderr.write('Python setuptools required, please install.')
    sys.exit(1)

version = open('lib/ec2utils/base_VERSION').read().strip()

if __name__ == '__main__':
    setuptools.setup(
        name='ec2utilsbase',
        description=(
            'Command-line tool to upload EC2 images'),
        long_description=open('README.md').read(),
        url='https://github.com/SUSE/Enceladus/tree/master/ec2utils',
        license='GPL-3.0+',
        install_requires=[ 'boto3>=1.3.0' ],
        author='SUSE Public Cloud Team',
        author_email='public-cloud-dev@susecloud.net',
        version=version,
        packages=setuptools.find_packages('lib'),
        package_data={'ec2utils': ['base_VERSION']},
        package_dir={
            '': 'lib',
        },
        namespace_packages = ['ec2utils'],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Natural Language :: English',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
        ]
    )
