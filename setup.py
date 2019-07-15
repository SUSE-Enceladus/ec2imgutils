#!/usr/bin/env python
"""Setup module for ec2imgutils"""

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
# along with ec2imgutils. If not, see <http://www.gnu.org/licenses/>.

import sys

try:
    import setuptools
except ImportError:
    sys.stderr.write('Python setuptools required, please install.')
    sys.exit(1)

version = open('lib/ec2imgutils/VERSION').read().strip()

with open('requirements.txt') as req_file:
    requirements = req_file.read().splitlines()

with open('requirements-dev.txt') as req_file:
    dev_requirements = req_file.read().splitlines()[2:]

if __name__ == '__main__':
    setuptools.setup(
        name='ec2imgutils',
        description=(
            'Command-line tools to manage images in AWS EC2'
        ),
        long_description=open('README.md').read(),
        long_description_content_type="text/markdown",
        url='https://github.com/SUSE-Enceladus/ec2imgutils',
        license='GPLv3+',
        install_requires=requirements,
        extras_require={
            'dev': dev_requirements
        },
        author='SUSE Public Cloud Team',
        author_email='public-cloud-dev@susecloud.net',
        version=version,
        packages=setuptools.find_packages('lib'),
        package_data={'ec2imgutils': ['VERSION']},
        package_dir={
            '': 'lib',
        },
        scripts=[
            'ec2deprecateimg',
            'ec2publishimg',
            'ec2removeimg',
            'ec2uploadimg'
        ],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Natural Language :: English',
            'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
        ]
    )
