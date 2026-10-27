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

## Test
```
> pyenv virtualenv 3.9.21 ec2imgutils
> pyenv activate ec2imgutils
> pip install -e .
> pytest
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
- Replacement image -> The AMI ID and name of the replacement image (Optional)

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

A command line utility to upload a raw image file, as created by
KIWI for example, to Amazon EC2 and create a snapshot or register an EBS
backed AMI. The image may be xz compressed or contained in a tar archive.
The image is written directly to a new EBS snapshot using the EBS direct
APIs, no helper instance is needed. The apparent size of the raw image is
recommended to be 10 GB or less and must not exceed the root volume size. It
is expected that the raw image has 1 partition, i.e. the root partition is
_/dev/sda1._ Only HVM images are supported. The process of creating the image
is as follows:

* Start a snapshot
* Read the image, decompress it on the fly and write it in blocks to the
  snapshot using multiple threads (_--upload-workers_), blocks containing only
  zeros are skipped
* Complete the snapshot
* Register a new AMI
* Clean up, an incomplete snapshot is deleted if an error occurs

The credentials need permission for the EBS direct API actions
`ebs:StartSnapshot`, `ebs:PutSnapshotBlock` and `ebs:CompleteSnapshot` as well
as for the EC2 actions `ec2:DescribeImages`, `ec2:DescribeSnapshots`,
`ec2:DeleteSnapshot`, `ec2:RegisterImage` and `ec2:CreateTags`.

Earlier versions uploaded the image with ssh to a helper instance and also
supported the root swap method and para-virtual images. This is no longer the
case. `--use-root-swap` and a virtualization type other than _hvm_ are
rejected. The options that configured the helper instance or the boot kernel
(_--ec2-ami_, _--instance-id_, _--ssh-key-pair_, _--private-key-file_,
_--user_, _--type_, _--ssh-timeout_, _--channel-timeout_,
_--security-group-ids_, _--vpc-subnet-id_, _--use-private-ip_,
_--use-enclave_, _--boot-kernel_, _--grub2_) are deprecated, a warning is
issued and they are ignored. The matching entries in the configuration file
are not used anymore.

#### Usage

```
> ec2uploadimg --account example -d "My first image" -m x86_64 -n my_linux_image -r us-east-1 PATH_TO_COMPRESSED_FILE
```

See the [man pages](man/man1/ec2uploadimg.1) for more information.

```
man ec2uploadimg
```
