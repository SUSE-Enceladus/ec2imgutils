#
# spec file for package python-ec2utilsbase
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


%define upstream_name ec2utilsbase
Name:           python3-ec2utilsbase
Version:        3.1.1
Release:        0
Summary:        Shared EC2 utils functionality
License:        GPL-3.0+
Group:          System/Management
Url:            https://github.com/SUSE/Enceladus
Source0:        %{upstream_name}-%{version}.tar.bz2
Requires:       python3
Requires:       python3-boto3 >= 1.3.0
BuildRequires:  python3-boto3 >= 1.3.0
BuildRequires:  python3-setuptools
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

# Package renamed in SLE 12, do not remove Provides, Obsolete directives
# until after SLE 12 EOL
Provides:       python-ec2utilsbase = %{version}
Obsoletes:      python-ec2utilsbase < %{version}

%description
Shared functionality for various ec2utils

%prep
%setup -q -n %{upstream_name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --prefix=%{_prefix} --root=%{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE
%dir %{python3_sitelib}/ec2utils
%{python3_sitelib}/*

%changelog
