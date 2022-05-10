[![Build Status](https://www.travis-ci.com/SUSE-Enceladus/ec2imgutils.svg?branch=master)](https://www.travis-ci.com/SUSE-Enceladus/ec2imgutils)

ec2imgutils
===========

A collection of utilities for image management in AWS EC2

## Installation

### openSUSE and SUSE Linux Enterprise

```
> zypper in python3-ec2imgutils
```

### PyPI

```
> pip install ec2imgutils
```

## Utilities

### ec2deprecateimg

A command line utility to deprecate images in Amazon EC2. The platform does
not support a formal deprecation mechanism. The mechansim implemented by this
tool is a convention. Unfortunately the tags are not sticky, i.e. not visible
to others if the image is shared.

Images are tagged with:

- Deprecated on -> provided deprecation date or today's date (if no deprecation
 date is provided) in YYYYMMDD format
- Removal date -> deprecation date plus the deprecation period specified
- Replacement image -> The AMI ID and name of the replacement image

The image set as the replacement is removed from the list of potential
images to be deprecated before any matching takes place. Therefore, the
deprecation search criteria specified with _--image-name-frag_ or
_--image-name-match_ cannot match the replacement image.

#### Usage

```
> ec2deprecateimg --account example --image-name-match v15 --image-virt-type hvm \
--replacement-name exampleimage_v16 --deprecation_date 20220510
```

See the [man pages](man/man1/ec2deprecateimg.1) for more information.

```
man ec2deprecateimg
```

### ec2listimg

A command line utility to list the AMIs in an account.

#### Usage

```
> ec2listimg --account example --image-name-frag foo --region us-west-2
```

See the [man pages](man/man1/ec2listimg.1) for more information.

```
man ec2listimg
```

### ec2publishimg

A command line utility to control the visibility of an image in AWS EC2.
The utility sets the visibility of an AMI to allow others to use the
image, making it public or sharing it with sepecific accounts, or setting
the image to private, i.e. only available to the account owner.

#### Usage

```
> ec2publishimg --account example --image-name-match production-v2 --share-with all
```

See the [man pages](man/man1/ec2publishimg.1) for more information.

```
man ec2publishimg
```

### ec2removeimg

A command line utility to remove images in Amazon EC2. Removing an image,
in the sense that all traces of a given image are gone, means the image
(AMI) has to be deregistered and the associated snapshot has to be deleted.
Having to do this in multiple regions in the UI is tedious and from the
the command line is a bookkeeping annoyance. This tool handles the clean up
of images.

#### Usage

```
> ec2removeimg --account example --image-name-match v15
```

See the [man pages](man/man1/ec2uploadimg.1) for more information.

```
man ec2removeimg
```

### ec2uploadimg

A command line utility to upload a compressed raw image file, as created by
KIWI for example to Amazon EC2 and create a snapshot or register an EBS
backed AMI. Uploads a compressed raw image to Amazon EC2 using an
existing EC2 AMI and creates a snapshot or registers a new AMI from the
image. The apparent size of the raw image is recommended to be 10 GB or
less. It is expected that the raw image has 1 partition, i.e. the root
partition is _/dev/sda1._ The process of creating the image is as
follows:

* Start an instance
* Create a storage volume and attach it to the running instance
* Create volume that will be the new root and attach it to the running 
  instance
* Upload the image
* Unpack the image and dump it to the new root volume
* Detach the new root volume and create a snapshot
* Register a new AMI
* Clean up

#### Usage

```
> ec2uploadimg --account example -d "My first image" -m x86_64 -n my_linux_image -r us-east-1 PATH_TO_COMPRESSED_FILE
```

See the [man pages](man/man1/ec2uploadimg.1) for more information.

```
man ec2uploadimg
```
