#
# spec file for package python-ec2uploadimg
#
# Copyright (c) 2015 SUSE LINUX Products GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#


%define upstream_name ec2uploadimg
Name:           python3-ec2uploadimg
Version:        5.0.6
Release:        0
Summary:        Upload an image to EC2
License:        GPL-3.0+
Group:          System/Management
Url:            https://github.com/SUSE/Enceladus
Source0:        %{upstream_name}-%{version}.tar.bz2
Requires:       python3
Requires:       python3-boto3        >= 1.4.1
Requires:       python3-ec2utilsbase >= 3.0.0
Requires:       python3-ec2utilsbase < 4.0.0
Requires:       python3-paramiko
BuildRequires:  python3-boto3        >= 1.4.1
BuildRequires:  python3-ec2utilsbase >= 3.0.0
BuildRequires:  python3-ec2utilsbase < 4.0.0
BuildRequires:  python3-paramiko
BuildRequires:  python3-setuptools
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

# Package renamed in SLE 12, do not remove Provides, Obsolete directives
# until after SLE 12 EOL
Provides:       python-ec2uploadimg = %{version}
Obsoletes:      python-ec2uploadimg < %{version}

%description
Upload a compressed .raw disk image to Amazon EC2 and create a snapshot
or register and AMI.

%prep
%setup -q -n %{upstream_name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --prefix=%{_prefix} --root=%{buildroot}
install -d -m 755 %{buildroot}/%{_mandir}/man1
install -m 644 man/man1/ec2uploadimg.1 %{buildroot}/%{_mandir}/man1
gzip %{buildroot}/%{_mandir}/man1/ec2uploadimg.1

%files
%defattr(-,root,root,-)
%doc LICENSE
%{_mandir}/man*/*
%dir %{python3_sitelib}/ec2utils
%{python3_sitelib}/*
%{_bindir}/*

%changelog
