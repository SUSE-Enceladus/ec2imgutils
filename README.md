ec2imgutils
===========

A collection of utilities for image management in AWS EC2

Utilities:

ec2deprecateimg
===============

A command line utility to deprecate images in Amazon EC2. The platform does
not support a formal deprecation mechanism. The mechansim implemented by this
tool is a convention. Unfortunately the tags are not sticky, i.e. not visible
to others if the image is shared.

Images are tagged with:
- Deprecated on     -> today's date in YYYYMMDD format
- Removal date      -> today's date plus the deprecation period specified
- Replacement image -> The AMI ID and name of the replacement image

