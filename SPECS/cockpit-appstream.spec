#
# Copyright (C) 2014-2020 Red Hat, Inc.
#
# Cockpit is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# Cockpit is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Cockpit; If not, see <http://www.gnu.org/licenses/>.
#

# This file is maintained at the following location:
# https://github.com/cockpit-project/cockpit/blob/main/tools/cockpit.spec
#
# If you are editing this file in another location, changes will likely
# be clobbered the next time an automated release is done.
#
# Check first cockpit-devel@lists.fedorahosted.org
#

# earliest base that the subpackages work on; this is still required as long as
# we maintain the basic/optional split, then it can be replaced with just %{version}.
%define required_base 266

%define machines_version 284.1

# we generally want CentOS packages to be like RHEL; special cases need to check %{centos} explicitly
%if 0%{?centos}
%define rhel %{centos}
%endif

%define _hardened_build 1

%define __lib lib

%if %{defined _pamdir}
%define pamdir %{_pamdir}
%else
%define pamdir %{_libdir}/security
%endif

Name:           cockpit-appstream
Summary:        Web Console for Linux servers

License:        LGPLv2+
URL:            https://cockpit-project.org/

Version:        286.2
Release:        1%{?dist}
Source0:        https://github.com/cockpit-project/cockpit/releases/download/%{version}/cockpit-%{version}.tar.xz
Source1:        https://github.com/cockpit-project/cockpit-machines/releases/download/%{machines_version}/cockpit-machines-%{machines_version}.tar.xz

# in RHEL 8 the source package is duplicated: cockpit (building basic packages like cockpit-{bridge,system})
# and cockpit-appstream (building optional packages like cockpit-{pcp})
# This split does not apply to EPEL/COPR nor packit c8s builds, only to our own
# image-prepare rhel-8-Y builds (which will disable build_all).
# In Fedora ELN/RHEL 9+ there is just one source package, which ships rpms in both BaseOS and AppStream
%define build_all 0
%if 0%{?rhel} == 8 && 0%{?epel} == 0 && !0%{?build_all}

%if "%{name}" == "cockpit"
%define build_basic 1
%define build_optional 0
%else
%define build_basic 0
%define build_optional 1
%endif

%else
%define build_basic 1
%define build_optional 1
%endif

# Allow root login in Cockpit on RHEL 8 and lower as it also allows password login over SSH.
%if 0%{?rhel} && 0%{?rhel} <= 8
%define disallow_root 0
%else
%define disallow_root 1
%endif

# Ship custom SELinux policy (but not for cockpit-appstream)
%if "%{name}" == "cockpit"
%define selinuxtype targeted
%define selinux_configure_arg --enable-selinux-policy=%{selinuxtype}
%endif

BuildRequires: gcc
BuildRequires: pkgconfig(gio-unix-2.0)
BuildRequires: pkgconfig(json-glib-1.0)
BuildRequires: pkgconfig(polkit-agent-1) >= 0.105
BuildRequires: pam-devel

BuildRequires: autoconf automake
BuildRequires: make
BuildRequires: /usr/bin/python3
%if 0%{?rhel} && 0%{?rhel} <= 8
# RHEL 8's gettext does not yet have metainfo.its
BuildRequires: gettext >= 0.19.7
BuildRequires: libappstream-glib-devel
%else
BuildRequires: gettext >= 0.21
%endif
%if 0%{?build_basic}
BuildRequires: libssh-devel >= 0.8.5
%endif
BuildRequires: openssl-devel
BuildRequires: gnutls-devel >= 3.4.3
BuildRequires: zlib-devel
BuildRequires: krb5-devel >= 1.11
BuildRequires: libxslt-devel
BuildRequires: glib-networking
BuildRequires: sed

BuildRequires: glib2-devel >= 2.50.0
# this is for runtimedir in the tls proxy ace21c8879
BuildRequires: systemd-devel >= 235
%if 0%{?suse_version}
BuildRequires: distribution-release
BuildRequires: libpcp-devel
BuildRequires: pcp-devel
BuildRequires: libpcp3
BuildRequires: libpcp_import1
BuildRequires: openssh
BuildRequires: distribution-logos
BuildRequires: wallpaper-branding
%else
BuildRequires: pcp-libs-devel
BuildRequires: openssh-clients
BuildRequires: docbook-style-xsl
%endif
BuildRequires: krb5-server
BuildRequires: gdb

# For documentation
BuildRequires: xmlto

BuildRequires:  selinux-policy
BuildRequires:  selinux-policy-devel

# This is the "cockpit" metapackage. It should only
# Require, Suggest or Recommend other cockpit-xxx subpackages

Requires: cockpit-bridge
Requires: cockpit-ws
Requires: cockpit-system

# Optional components
Recommends: (cockpit-storaged if udisks2)
Recommends: (cockpit-packagekit if dnf)
Suggests: cockpit-pcp

%if 0%{?rhel} == 0
Recommends: (cockpit-networkmanager if NetworkManager)
Suggests: cockpit-selinux
%endif
%if 0%{?rhel} && 0%{?centos} == 0
Requires: subscription-manager-cockpit
%endif

%prep
%setup -q -T -a 1 -c -n cockpit-machines-%{machines_version}
%setup -q -n cockpit-%{version}

%build
%configure \
    %{?selinux_configure_arg} \
    --with-cockpit-user=cockpit-ws \
    --with-cockpit-ws-instance-user=cockpit-wsinstance \
%if 0%{?suse_version}
    --docdir=%_defaultdocdir/%{name} \
%endif
    --with-pamdir='%{pamdir}' \
%if 0%{?build_basic} == 0
    --disable-ssh \
%endif

%make_build

%check
make -j$(nproc) check

%install
%make_install
make install-tests DESTDIR=%{buildroot}
make -C %{_builddir}/cockpit-machines-%{machines_version}/cockpit-machines install DESTDIR=%{buildroot}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/pam.d
install -p -m 644 tools/cockpit.pam $RPM_BUILD_ROOT%{_sysconfdir}/pam.d/cockpit
rm -f %{buildroot}/%{_libdir}/cockpit/*.so
install -D -p -m 644 AUTHORS COPYING README.md %{buildroot}%{_docdir}/cockpit/

# Build the package lists for resource packages
# cockpit-bridge is the basic dependency for all cockpit-* packages, so centrally own the page directory
echo '%dir %{_datadir}/cockpit' > base.list
echo '%dir %{_datadir}/cockpit/base1' >> base.list
find %{buildroot}%{_datadir}/cockpit/base1 -type f -o -type l >> base.list
echo '%{_sysconfdir}/cockpit/machines.d' >> base.list
echo %{buildroot}%{_datadir}/polkit-1/actions/org.cockpit-project.cockpit-bridge.policy >> base.list
echo '%dir %{_datadir}/cockpit/ssh' >> base.list
find %{buildroot}%{_datadir}/cockpit/ssh -type f >> base.list
echo '%{_libexecdir}/cockpit-ssh' >> base.list

echo '%dir %{_datadir}/cockpit/pcp' > pcp.list
find %{buildroot}%{_datadir}/cockpit/pcp -type f >> pcp.list

echo '%dir %{_datadir}/cockpit/tuned' > system.list
find %{buildroot}%{_datadir}/cockpit/tuned -type f >> system.list

echo '%dir %{_datadir}/cockpit/shell' >> system.list
find %{buildroot}%{_datadir}/cockpit/shell -type f >> system.list

echo '%dir %{_datadir}/cockpit/systemd' >> system.list
find %{buildroot}%{_datadir}/cockpit/systemd -type f >> system.list

echo '%dir %{_datadir}/cockpit/users' >> system.list
find %{buildroot}%{_datadir}/cockpit/users -type f >> system.list

echo '%dir %{_datadir}/cockpit/metrics' >> system.list
find %{buildroot}%{_datadir}/cockpit/metrics -type f >> system.list

echo '%dir %{_datadir}/cockpit/kdump' > kdump.list
find %{buildroot}%{_datadir}/cockpit/kdump -type f >> kdump.list

echo '%dir %{_datadir}/cockpit/sosreport' > sosreport.list
find %{buildroot}%{_datadir}/cockpit/sosreport -type f >> sosreport.list

echo '%dir %{_datadir}/cockpit/storaged' > storaged.list
find %{buildroot}%{_datadir}/cockpit/storaged -type f >> storaged.list

echo '%dir %{_datadir}/cockpit/networkmanager' > networkmanager.list
find %{buildroot}%{_datadir}/cockpit/networkmanager -type f >> networkmanager.list

echo '%dir %{_datadir}/cockpit/packagekit' > packagekit.list
find %{buildroot}%{_datadir}/cockpit/packagekit -type f >> packagekit.list

echo '%dir %{_datadir}/cockpit/apps' >> packagekit.list
find %{buildroot}%{_datadir}/cockpit/apps -type f >> packagekit.list

echo '%dir %{_datadir}/cockpit/machines' > machines.list
find %{buildroot}%{_datadir}/cockpit/machines -type f >> machines.list

echo '%dir %{_datadir}/cockpit/selinux' > selinux.list
find %{buildroot}%{_datadir}/cockpit/selinux -type f >> selinux.list

echo '%dir %{_datadir}/cockpit/playground' > tests.list
find %{buildroot}%{_datadir}/cockpit/playground -type f >> tests.list

echo '%dir %{_datadir}/cockpit/static' > static.list
echo '%dir %{_datadir}/cockpit/static/fonts' >> static.list
find %{buildroot}%{_datadir}/cockpit/static -type f >> static.list

# when not building basic packages, remove their files
%if 0%{?build_basic} == 0
for pkg in base1 branding motd kdump networkmanager selinux shell sosreport ssh static systemd tuned users metrics; do
    rm -r %{buildroot}/%{_datadir}/cockpit/$pkg
    rm -f %{buildroot}/%{_datadir}/metainfo/org.cockpit-project.cockpit-${pkg}.metainfo.xml
done
for data in doc man pixmaps polkit-1; do
    rm -r %{buildroot}/%{_datadir}/$data
done
rm -r %{buildroot}/%{_prefix}/%{__lib}/tmpfiles.d
find %{buildroot}/%{_unitdir}/ -type f ! -name 'cockpit-session*' -delete
for libexec in cockpit-askpass cockpit-session cockpit-ws cockpit-tls cockpit-wsinstance-factory cockpit-client cockpit-client.ui cockpit-desktop cockpit-certificate-helper cockpit-certificate-ensure; do
    rm %{buildroot}/%{_libexecdir}/$libexec
done
rm -r %{buildroot}/%{_sysconfdir}/pam.d %{buildroot}/%{_sysconfdir}/motd.d %{buildroot}/%{_sysconfdir}/issue.d
rm -f %{buildroot}/%{_libdir}/security/pam_*
rm %{buildroot}/usr/bin/cockpit-bridge
rm -f %{buildroot}%{_libexecdir}/cockpit-ssh
rm -f %{buildroot}%{_datadir}/metainfo/cockpit.appdata.xml
%endif

# when not building optional packages, remove their files
%if 0%{?build_optional} == 0
for pkg in apps packagekit pcp playground storaged; do
    rm -rf %{buildroot}/%{_datadir}/cockpit/$pkg
done
# files from -tests
rm -f %{buildroot}/%{pamdir}/mock-pam-conv-mod.so
rm -f %{buildroot}/%{_unitdir}/cockpit-session.socket
rm -f %{buildroot}/%{_unitdir}/cockpit-session@.service
# files from -pcp
rm -r %{buildroot}/%{_libexecdir}/cockpit-pcp %{buildroot}/%{_localstatedir}/lib/pcp/
# files from -storaged
rm -f %{buildroot}/%{_prefix}/share/metainfo/org.cockpit-project.cockpit-storaged.metainfo.xml
%endif

sed -i "s|%{buildroot}||" *.list

%if ! 0%{?suse_version}
%global _debugsource_packages 1
%global _debuginfo_subpackages 0

%define find_debug_info %{_rpmconfigdir}/find-debuginfo.sh %{?_missing_build_ids_terminate_build:--strict-build-id} %{?_include_minidebuginfo:-m} %{?_find_debuginfo_dwz_opts} %{?_find_debuginfo_opts} %{?_debugsource_packages:-S debugsourcefiles.list} "%{_builddir}/%{?buildsubdir}"

%endif
# /suse_version
rm -rf %{buildroot}/usr/src/debug

# On RHEL kdump, networkmanager, selinux, and sosreport are part of the system package
%if 0%{?rhel}
cat kdump.list sosreport.list networkmanager.list selinux.list >> system.list
rm -f %{buildroot}%{_datadir}/metainfo/org.cockpit-project.cockpit-sosreport.metainfo.xml
rm -f %{buildroot}%{_datadir}/metainfo/org.cockpit-project.cockpit-kdump.metainfo.xml
rm -f %{buildroot}%{_datadir}/metainfo/org.cockpit-project.cockpit-selinux.metainfo.xml
rm -f %{buildroot}%{_datadir}/metainfo/org.cockpit-project.cockpit-networkmanager.metainfo.xml
rm -f %{buildroot}%{_datadir}/pixmaps/cockpit-sosreport.png
%endif

# -------------------------------------------------------------------------------
# Basic Sub-packages

%if 0%{?build_basic}

%description
The Cockpit Web Console enables users to administer GNU/Linux servers using a
web browser.

It offers network configuration, log inspection, diagnostic reports, SELinux
troubleshooting, interactive command-line sessions, and more.

%files
%{_docdir}/cockpit/AUTHORS
%{_docdir}/cockpit/COPYING
%{_docdir}/cockpit/README.md
%{_datadir}/metainfo/cockpit.appdata.xml
%{_datadir}/pixmaps/cockpit.png
%doc %{_mandir}/man1/cockpit.1.gz


%package bridge
Summary: Cockpit bridge server-side component
Requires: glib-networking
Provides: cockpit-ssh = %{version}-%{release}
# 233 dropped jquery.js, pages started to bundle it (commit 049e8b8dce)
Conflicts: cockpit-dashboard < 233
Conflicts: cockpit-networkmanager < 233
Conflicts: cockpit-storaged < 233
Conflicts: cockpit-system < 233
Conflicts: cockpit-tests < 233
Conflicts: cockpit-docker < 233

%description bridge
The Cockpit bridge component installed server side and runs commands on the
system on behalf of the web based user interface.

%files bridge -f base.list
%doc %{_mandir}/man1/cockpit-bridge.1.gz
%{_bindir}/cockpit-bridge
%{_libexecdir}/cockpit-askpass

%package doc
Summary: Cockpit deployment and developer guide
BuildArch: noarch

%description doc
The Cockpit Deployment and Developer Guide shows sysadmins how to
deploy Cockpit on their machines as well as helps developers who want to
embed or extend Cockpit.

%files doc
%exclude %{_docdir}/cockpit/AUTHORS
%exclude %{_docdir}/cockpit/COPYING
%exclude %{_docdir}/cockpit/README.md
%{_docdir}/cockpit

%package system
Summary: Cockpit admin interface package for configuring and troubleshooting a system
BuildArch: noarch
Requires: cockpit-bridge >= %{version}-%{release}
%if !0%{?suse_version}
Requires: shadow-utils
%endif
Requires: grep
Requires: /usr/bin/pwscore
Requires: /usr/bin/date
Provides: cockpit-shell = %{version}-%{release}
Provides: cockpit-systemd = %{version}-%{release}
Provides: cockpit-tuned = %{version}-%{release}
Provides: cockpit-users = %{version}-%{release}
Obsoletes: cockpit-dashboard < %{version}-%{release}
%if 0%{?rhel}
Requires: NetworkManager >= 1.6
Requires: kexec-tools
Requires: sos
Requires: sudo
Recommends: PackageKit
Recommends: setroubleshoot-server >= 3.3.3
Suggests: NetworkManager-team
Provides: cockpit-kdump = %{version}-%{release}
Provides: cockpit-networkmanager = %{version}-%{release}
Provides: cockpit-selinux = %{version}-%{release}
Provides: cockpit-sosreport = %{version}-%{release}
%endif
%if 0%{?fedora}
Recommends: (reportd if abrt)
%endif

%description system
This package contains the Cockpit shell and system configuration interfaces.

%files system -f system.list
%dir %{_datadir}/cockpit/shell/images

%package ws
Summary: Cockpit Web Service
Requires: glib-networking
Requires: openssl
Requires: glib2 >= 2.50.0
Requires: (selinux-policy >= %{_selinux_policy_version} if selinux-policy-%{selinuxtype})
Requires(post): (policycoreutils if selinux-policy-%{selinuxtype})
Conflicts: firewalld < 0.6.0-1
Recommends: sscg >= 2.3
Recommends: system-logos
Suggests: sssd-dbus
# for cockpit-desktop
Suggests: python3

# prevent hard python3 dependency for cockpit-desktop, it falls back to other browsers
%global __requires_exclude_from ^%{_libexecdir}/cockpit-client$

%description ws
The Cockpit Web Service listens on the network, and authenticates users.

If sssd-dbus is installed, you can enable client certificate/smart card
authentication via sssd/FreeIPA.

%files ws -f static.list
%doc %{_mandir}/man1/cockpit-desktop.1.gz
%doc %{_mandir}/man5/cockpit.conf.5.gz
%doc %{_mandir}/man8/cockpit-ws.8.gz
%doc %{_mandir}/man8/cockpit-tls.8.gz
%doc %{_mandir}/man8/pam_ssh_add.8.gz
%dir %{_sysconfdir}/cockpit
%config(noreplace) %{_sysconfdir}/cockpit/ws-certs.d
%config(noreplace) %{_sysconfdir}/pam.d/cockpit
# created in %post, so that users can rm the files
%ghost %{_sysconfdir}/issue.d/cockpit.issue
%ghost %{_sysconfdir}/motd.d/cockpit
%ghost %attr(0644, root, root) %{_sysconfdir}/cockpit/disallowed-users
%dir %{_datadir}/cockpit/motd
%{_datadir}/cockpit/motd/update-motd
%{_datadir}/cockpit/motd/inactive.motd
%{_unitdir}/cockpit.service
%{_unitdir}/cockpit-motd.service
%{_unitdir}/cockpit.socket
%{_unitdir}/cockpit-wsinstance-http.socket
%{_unitdir}/cockpit-wsinstance-http.service
%{_unitdir}/cockpit-wsinstance-https-factory.socket
%{_unitdir}/cockpit-wsinstance-https-factory@.service
%{_unitdir}/cockpit-wsinstance-https@.socket
%{_unitdir}/cockpit-wsinstance-https@.service
%{_unitdir}/system-cockpithttps.slice
%{_prefix}/%{__lib}/tmpfiles.d/cockpit-tempfiles.conf
%{pamdir}/pam_ssh_add.so
%{pamdir}/pam_cockpit_cert.so
%{_libexecdir}/cockpit-ws
%{_libexecdir}/cockpit-wsinstance-factory
%{_libexecdir}/cockpit-tls
%{_libexecdir}/cockpit-client
%{_libexecdir}/cockpit-client.ui
%{_libexecdir}/cockpit-desktop
%{_libexecdir}/cockpit-certificate-ensure
%{_libexecdir}/cockpit-certificate-helper
%attr(4750, root, cockpit-wsinstance) %{_libexecdir}/cockpit-session
%{_datadir}/cockpit/branding
%{_datadir}/selinux/packages/%{selinuxtype}/%{name}.pp.bz2
%{_mandir}/man8/%{name}_session_selinux.8cockpit.*
%{_mandir}/man8/%{name}_ws_selinux.8cockpit.*
%ghost %{_sharedstatedir}/selinux/%{selinuxtype}/active/modules/200/%{name}

%pre ws
getent group cockpit-ws >/dev/null || groupadd -r cockpit-ws
getent passwd cockpit-ws >/dev/null || useradd -r -g cockpit-ws -d /nonexisting -s /sbin/nologin -c "User for cockpit web service" cockpit-ws
getent group cockpit-wsinstance >/dev/null || groupadd -r cockpit-wsinstance
getent passwd cockpit-wsinstance >/dev/null || useradd -r -g cockpit-wsinstance -d /nonexisting -s /sbin/nologin -c "User for cockpit-ws instances" cockpit-wsinstance

if %{_sbindir}/selinuxenabled 2>/dev/null; then
    %selinux_relabel_pre -s %{selinuxtype}
fi

%post ws
if [ -x %{_sbindir}/selinuxenabled ]; then
    %selinux_modules_install -s %{selinuxtype} %{_datadir}/selinux/packages/%{selinuxtype}/%{name}.pp.bz2
    %selinux_relabel_post -s %{selinuxtype}
fi

# set up dynamic motd/issue symlinks on first-time install; don't bring them back on upgrades if admin removed them
# disable root login on first-time install; so existing installations aren't changed
if [ "$1" = 1 ]; then
    mkdir -p /etc/motd.d /etc/issue.d
    ln -s ../../run/cockpit/motd /etc/motd.d/cockpit
    ln -s ../../run/cockpit/motd /etc/issue.d/cockpit.issue
    printf "# List of users which are not allowed to login to Cockpit\n" > /etc/cockpit/disallowed-users
%if 0%{?disallow_root}
    printf "root\n" >> /etc/cockpit/disallowed-users
%endif
    chmod 644 /etc/cockpit/disallowed-users
fi

%tmpfiles_create cockpit-tempfiles.conf
%systemd_post cockpit.socket cockpit.service
# firewalld only partially picks up changes to its services files without this
test -f %{_bindir}/firewall-cmd && firewall-cmd --reload --quiet || true

# check for deprecated PAM config
if grep --color=auto pam_cockpit_cert %{_sysconfdir}/pam.d/cockpit; then
    echo '**** WARNING:'
    echo '**** WARNING: pam_cockpit_cert is a no-op and will be removed in a'
    echo '**** WARNING: future release; remove it from your /etc/pam.d/cockpit.'
    echo '**** WARNING:'
fi

%preun ws
%systemd_preun cockpit.socket cockpit.service

%postun ws
if [ -x %{_sbindir}/selinuxenabled ]; then
    %selinux_modules_uninstall -s %{selinuxtype} %{name}
    %selinux_relabel_post -s %{selinuxtype}
fi
%systemd_postun_with_restart cockpit.socket cockpit.service

# -------------------------------------------------------------------------------
# Sub-packages that are part of cockpit-system in RHEL/CentOS, but separate in Fedora

%if 0%{?rhel} == 0

%package kdump
Summary: Cockpit user interface for kernel crash dumping
Requires: cockpit-bridge >= %{required_base}
Requires: cockpit-shell >= %{required_base}
Requires: kexec-tools
BuildArch: noarch

%description kdump
The Cockpit component for configuring kernel crash dumping.

%files kdump -f kdump.list
%{_datadir}/metainfo/org.cockpit-project.cockpit-kdump.metainfo.xml

%package sosreport
Summary: Cockpit user interface for diagnostic reports
Requires: cockpit-bridge >= %{required_base}
Requires: cockpit-shell >= %{required_base}
Requires: sos
BuildArch: noarch

%description sosreport
The Cockpit component for creating diagnostic reports with the
sosreport tool.

%files sosreport -f sosreport.list
%{_datadir}/metainfo/org.cockpit-project.cockpit-sosreport.metainfo.xml
%{_datadir}/pixmaps/cockpit-sosreport.png

%package networkmanager
Summary: Cockpit user interface for networking, using NetworkManager
Requires: cockpit-bridge >= %{required_base}
Requires: cockpit-shell >= %{required_base}
Requires: NetworkManager >= 1.6
# Optional components
Recommends: NetworkManager-team
BuildArch: noarch

%description networkmanager
The Cockpit component for managing networking.  This package uses NetworkManager.

%files networkmanager -f networkmanager.list
%{_datadir}/metainfo/org.cockpit-project.cockpit-networkmanager.metainfo.xml

%endif

%if 0%{?rhel} == 0

%package selinux
Summary: Cockpit SELinux package
Requires: cockpit-bridge >= %{required_base}
Requires: cockpit-shell >= %{required_base}
Requires: setroubleshoot-server >= 3.3.3
BuildArch: noarch

%description selinux
This package contains the Cockpit user interface integration with the
utility setroubleshoot to diagnose and resolve SELinux issues.

%files selinux -f selinux.list
%{_datadir}/metainfo/org.cockpit-project.cockpit-selinux.metainfo.xml

%endif

#/ build basic packages
%else

# RPM requires this
%description
Dummy package from building optional packages only; never install or publish me.

#/ build basic packages
%endif

# -------------------------------------------------------------------------------
# Sub-packages that are optional extensions

%if 0%{?build_optional}

%package -n cockpit-storaged
Summary: Cockpit user interface for storage, using udisks
Requires: cockpit-shell >= %{required_base}
Requires: udisks2 >= 2.9
Recommends: udisks2-lvm2 >= 2.9
Recommends: udisks2-iscsi >= 2.9
Recommends: device-mapper-multipath
Recommends: clevis-luks
Requires: %{__python3}
%if 0%{?suse_version}
Requires: python3-dbus-python
%else
Requires: python3-dbus
%endif
BuildArch: noarch

%description -n cockpit-storaged
The Cockpit component for managing storage.  This package uses udisks.

%files -n cockpit-storaged -f storaged.list
%dir %{_datadir}/cockpit/storaged/images
%{_datadir}/metainfo/org.cockpit-project.cockpit-storaged.metainfo.xml

%package -n cockpit-tests
Summary: Tests for Cockpit
Requires: cockpit-bridge >= %{required_base}
Requires: cockpit-system >= %{required_base}
Requires: openssh-clients
Provides: cockpit-test-assets = %{version}-%{release}

%description -n cockpit-tests
This package contains tests and files used while testing Cockpit.
These files are not required for running Cockpit.

%files -n cockpit-tests -f tests.list
%{pamdir}/mock-pam-conv-mod.so
%{_unitdir}/cockpit-session.socket
%{_unitdir}/cockpit-session@.service

%package -n cockpit-machines
BuildArch: noarch
Summary: Cockpit user interface for virtual machines
Requires: cockpit-bridge >= 215
Requires: libvirt-daemon-driver-qemu
Requires: libvirt-daemon-driver-network
Requires: libvirt-daemon-driver-nodedev
Requires: libvirt-daemon-driver-storage-core
Requires: (libvirt-daemon-driver-interface if virt-install)
Requires: (libvirt-daemon-config-network if virt-install)
Recommends: libvirt-daemon-driver-storage-disk
Requires: qemu-kvm
Requires: libvirt-client
Requires: libvirt-dbus >= 1.2.0
# Optional components
Recommends: virt-install >= 3.0.0
Recommends: libosinfo
Recommends: python3-gobject-base
Suggests: qemu-virtiofsd

%description -n cockpit-machines
The Cockpit components for managing virtual machines.

If "virt-install" is installed, you can also create new virtual machines.

%files -n cockpit-machines -f machines.list
%{_datadir}/metainfo/org.cockpit-project.machines.metainfo.xml

%package -n cockpit-pcp
Summary: Cockpit PCP integration
Requires: cockpit-bridge >= %{required_base}
Requires: pcp

%description -n cockpit-pcp
Cockpit support for reading PCP metrics and loading PCP archives.

%files -n cockpit-pcp -f pcp.list
%{_libexecdir}/cockpit-pcp
%{_localstatedir}/lib/pcp/config/pmlogconf/tools/cockpit

%post -n cockpit-pcp
systemctl reload-or-try-restart pmlogger

%package -n cockpit-packagekit
Summary: Cockpit user interface for packages
BuildArch: noarch
Requires: cockpit-bridge >= %{required_base}
Requires: PackageKit
Recommends: python3-tracer
# HACK: https://bugzilla.redhat.com/show_bug.cgi?id=1800468
Requires: polkit

%description -n cockpit-packagekit
The Cockpit components for installing OS updates and Cockpit add-ons,
via PackageKit.

%files -n cockpit-packagekit -f packagekit.list

#/ build optional extension packages
%endif

# The changelog is automatically generated and merged
%changelog
* Mon Jun 05 2023 Martin Pitt <mpitt@redhat.com> - 286.2-1
- storage: When fixing NBDE, also recognize indirect root filesystems (rhbz#2212371)

* Thu Feb 23 2023 Martin Pitt <mpitt@redhat.com> - 286.1-1
- Translation updates (rhbz#2139719)

* Wed Feb 22 2023 Martin Pitt <mpitt@redhat.com> - 286-1
- Stability and performance improvements

* Wed Feb 08 2023 Martin Pitt <mpitt@redhat.com> - 285-1
- Stability and performance improvements

* Thu Jan 26 2023 Martin Pitt <mpitt@redhat.com> - 284-1
- Storage: Set up a system to use NBDE
- Machines: Option to forcefully revert a snapshot
- Fix tabular numbers font

* Wed Jan 11 2023 Katerina Koukiou <kkoukiou@redhat.com> - 283-1
- Machines: Summarize system and user session differences
- Machines: Virtual watchdog device support

* Wed Nov 23 2022 Matej Marusak <mmarusak@redhat.com> - 278-1
- Machines: Allow TRIM/UNMAP requests by default for newly added disks
- Machines: Insert and eject CD & DVD media

* Thu Aug 25 2022 Matej Marusak <mmarusak@redhat.com> - 275-1
- Machines: Offer downloading RHEL OS only for RHEL >= 8 (rhbz#2118236)

* Thu Jul 21 2022 Martin Pitt <mpitt@redhat.com> - 273-1
 - Software Updates: Optionally reboot after updating
 - Machines: Show toast notication if VM's storage deletion fails (rhbz#2105984)

* Thu Jun 23 2022 Matej Marusak <mmarusak@redhat.com> - 272-1
- Translation updates

* Wed May 25 2022 Martin Pitt <mpitt@redhat.com> - 270-1
- Machines: Redesign content removal dialogs

* Mon May 16 2022 Martin Pitt <mpitt@redhat.com> - 269-1
- Show base-10 units by default (rhbz#1970119)
- Apps: Fix i18n (rhbz#2018389)
- Software Updates: Install kpatches only (rhbz#2039989)
- Machines: Fix deleting net interfaces with non-unique MAC address (rhbz#1867478)
- Machines: Create disks with random/customizable serial number (rhbz#2036330)
- Machines: Fix network interface source icon (rhbz#2063680)

* Fri Feb 25 2022 Martin Pitt <mpitt@redhat.com> - 264-1
- Machines: Fix broken VM deletion dialog layout
- Translation updates

* Thu Feb 17 2022 Martin Pitt <mpitt@redhat.com> - 263-1
- Overview: Show scheduled shutdowns
- Networking: Add firewall service description
- Shell: Fix browser history

* Tue Jan 25 2022 Matej Marusak <mmarusak@redhat.com> - 261-1
- storage: Unmounting or deleting a busy filesystem is now supported
- Tests improvements and stabilization
- Machines: Delete disks only after VM is successfully undefined and destroyed (rhbz#2031678)
- Machines: Do not change "startVm" value when selecting Unattended installation (rhbz#2033603)

* Tue Dec 14 2021 Martin Pitt <mpitt@redhat.com> - 259-1
- Use official VDO LVM API

* Fri Nov 12 2021 Katerina Koukiou <kkoukiou@redhat.com> - 257-1
- Machines: Now officially supported on Arch Linux (https://archlinux.org/)
- Machines: Support selecting between consoles of the same type

* Thu Oct 14 2021 Martin Pitt <mpitt@redhat.com> - 255-1
- Machines: Parse supported disk bus types from domcapabities (rhbz#1862779)
- Machines: Stop exposing unattended installation option for ISO installation
  media (rhbz#1868594)

* Thu Aug 19 2021 Matej Marusak <mmarusak@redhat.com> - 251-1
- Machines: Always show current disk bus type (rhbz#1985256)

* Wed Aug 04 2021 Martin Pitt <mpitt@redhat.com> - 250-1
- Software Updates: Introduce basic kpatch support
- Software Updates: Handle unregistered RHEL systems with non-CDN OS repository
  (rhbz#1970057)
- Machines: Read qemu.conf to get spice/vnc address (rhbz#1963701)

* Wed Jul 21 2021 Matej Marusak <mmarusak@redhat.com> - 249-1
- Machines: Fix input for "Target Path" when Creating storage pool (rhbz#1866225)
- Machines: Don't round or floor memory and storage size unnecessarily (rhbz#1979152)
- Machines: Use cockpit's proxy API for monitoring libvirt service changes (rhbz#1974223)
- Machines: Fix ooops when press the down arrow several times when inputting custom path (rhbz#1977554)

* Fri Jul 09 2021 Katerina Koukiou <kkoukiou@redhat.com> - 248-1
- Machines: Share host files with the guest using virtiofs
- Machines: Show list of pass-through devices

* Tue Jun 15 2021 Martin Pitt <mpitt@redhat.com> - 246-1
- Polish of the Storage page
- Storage: Show both SHA256 and SHA1 Tang fingerprints
- Updated translations

* Tue May 18 2021 Martin Pitt <mpitt@redhat.com> - 244.1-1
- Machines: Edit the MAC address of a VM’s network interface

* Fri Apr 16 2021 Martin Pitt <mpitt@redhat.com> - 242-1
- Updates: Show subscription status on cloud images (rhbz#1931429)
- Machines: Allow creation of non-root user for unattended installations (rhbz#1940287)

* Mon Feb 22 2021 Martin Pitt <mpitt@redhat.com> - 238.1-1
- Several UI alignment fixes
- Updates: Show PackageKit errors properly

* Fri Feb 19 2021 Katerina Koukiou <kkoukiou@redhat.com> - 238-1
- machines: VM disk creation supports a custom path
- Updates: List outdated software that needs a restart

* Thu Feb 04 2021 Katerina Koukiou <kkoukiou@redhat.com> - 237-1
- machines: Fix virt-viewer file download on chromium based Edge (rhbz#1730666)
- machines: Fix crash when a target is pasted in the VM creation dialog (rhbz#1872660)
- machines: Fix alert about pending changes in NIC edit dialog (rhbz#1911657)
- machines: Fix alert about pending changes in overview card related to boot order (rhbz#1915765)
- machines: Fix file autocomplete select not closing on enter (rhbz#1874392)
- machines: Fix white screen when deleting a VM in an environment without storage pools (rhbz#1912384)

* Fri Jan 22 2021 Martin Pitt <mpitt@redhat.com> - 236-1
- machines: Fix unstable VNC console (rhbz#1750642)
- machines: Fix alert close property in the VM details (rhbz#1918147)
- machines: Fix crash when volumes disappear before starting installation (rhbz#1918156)
- machines: Fix crash when undefining created VM before starting installation (rhbz#1916597)
- machines: Fix shutting down transient VM (rhbz#1916595)
- machines: Fix VM detail page's "Install" button (rhbz#1916120)

* Fri Jan 08 2021 Matej Marusak <mmarusak@redhat.com> - 235-1
- machines: Fix check of cpu configuration between active/inactive XML (rhbz#1913205)
- machines: Fix rounding of memory when switching from MB to GB (rhbz#1908683)

* Mon Dec 14 2020 Katerina Koukiou <kkoukiou@redhat.com> - 234-1
- machines: Allow editing VM's CPU mode and model (rhbz#1683301)
- machines: Add support for cloning VMs (rhbz#1683391)
- dashboard: Drop cockpit-dashboard package, replaced with shell host switcher

* Fri Nov 27 2020 Katerina Koukiou <kkoukiou@redhat.com> - 233.1-1
- machines: Inline error messages (rhbz#1666829)
- machines: Reimplement the design of the main VMs list (rhbz#1780537, rhbz#1847712, rhbz#1858716, rhbz#1862406, rhbz#1873931)
- storage: List entries from /etc/crypttab that are still locked
- machines: Add support for reverting and deleting VM snapshots
- machines: Add support for VM snapshots (rhbz#1668870, rhbz#1673158)
- machines: Virtual machine list filtering
- storage: Better support for "noauto" LUKS devices
- machines: Fix 'PXE' installed VMs having network first in the boot order even after the installation finishded (rhbz#1859008)
- machines: Fix Desktop Viewer Console tab CSS issues (rhbz#1868584)
- tools: Fix duplicated -debuginfo files (rhbz#1870521)
- machines: Show cdrom details in bootorder dialog (rhbz#1880175)

* Wed Aug 19 2020 Matej Marusak <mmarusak@redhat.com> - 224.2-1
- lib: Include current directory in FileAutoComplete option listing (rhbz#1866995)
- lib: Make sure that the expandable part of table rows has unique key (rhbz#1865821)

* Wed Aug 05 2020 Matej Marusak <mmarusak@redhat.com> - 224.1-1
- machines: add padding to storage pools list cells (rhbz#1857500)
- machines: Fix OS autodetection in create VM dialog (rhbz#1862333)
- machines: Fix TypeError for OSRow in VM creation dialog (rhbz#1862106)

* Thu Jul 23 2020 Martin Pitt <mpitt@redhat.com> - 224-1
- Translation updates
- Machines: Remove creation of user account (rhbz#1853918)
- Machines: Fix reboot after PXE installation (rhbz#1853408, rhbz#1859045)
- Machines: Fix notification for transient VMs (rhbz#1853649)
- Machines: Make Storage/Network lists consistent with VM list (rhbz#1854257)
- Machines: Fix close button on NIC Edit modal dialog header (rhbz#1857044)

* Thu Jul 09 2020 Martin Pitt <mpitt@redhat.com> - 223-1
- Translation updates

* Fri Jun 26 2020 Matej Marusak <mmarusak@redhat.com> - 222.1-1
- Some integration test fixes for dist-git gating

* Wed Jun 24 2020 Matej Marusak <mmarusak@redhat.com> - 222-1
- Localization updates

* Sun Jun 14 2020 Martin Pitt <mpitt@redhat.com> - 221-1
- machines: Remove --noreboot parameter to virt-install for VM installation
  (rhbz#1750637)
- Translation updates

* Thu May 28 2020 Matej Marusak <mmarusak@redhat.com> - 220-1
- Storage: Improve side panel on details page

* Thu May 14 2020 Matej Marusak <mmarusak@redhat.com> - 219-1
- New upstream release 219
- Send key functionality for the virtual machines (rhbz#1693487)
- Fix dnf-automatic timer parsing (rhbz#1829685)

* Thu Mar 12 2020 Martin Pitt <mpitt@redhat.com> - 211.3-1
- Fix CJK translations (rhbz#1807333)

* Wed Feb 19 2020 Martin Pitt <mpitt@redhat.com> - 211.2.1
- Machines: Fix stuck delete dialogs (rhbz#1791543, #1792379)
- Machines: Fix CPU statistics (rhbz#1763641)
- Machines: Fix incorrect format when adding existing disk to VM (rhbz#1792319)
- Storage: Minor layout fixes
- Translation updates

* Thu Jan 23 2020 Matej Marusak <mmarusak@redhat.com> - 211-1
- Machines: The VM is covered when another one has the same name (rhbz#1780451)
- Machines: Decompress ipv6 addresses before validating them (rhbz#1784289)
- Machines: Fix default bridge selection for `Bridge to LAN` NIC (rhbz#1791537, rhbz#1791543)

* Thu Jan 09 2020 Matej Marusak <mmarusak@redhat.com> - 210-1
- Dashboard: Support SSH identity unlocking when adding new machines
- Machines: Support “bridge” type network interfaces
- Machines: Support “bus” type disk configuration (rhbz#1671144)
- Machines: Fix default storage pool search (rhbz#1778049)
- Machines: Fix lost of configuration changes made before installation (rhbz#1780449)
- Machines: Fix edit NIC dialog when the current network in XML was deleted (rhbz#1780452)
- Machines: Fix default volume format detection in Disk Add dialog (rhbz#1784304)
- Machines: Use all cells when getting Host Max Memory (rhbz#1780530)

* Fri Dec 13 2019 Matej Marusak <mmarusak@redhat.com> - 209-1
- Machines: Don't disable detaching button when VM is running (rhbz#1777201)
- Machines: Support transient virtual networks and storage pools (rhbz#1715429)
- Machines: Fix Oops when creating a VM from ISO on system with no storage pools (rhbz#1778049)
- Stop fetching variables from base1/patternfly.css because they can be outdated (rhbz#1777683)


* Thu Nov 28 2019 Matej Marusak <mmarusak@redhat.com> - 208-1
- Storage: Drop “default mount point” concept
- Machines: Support transient virtual networks and storage pools
- Machines: Sliders for disk size and memory in VM creation
- Storage: List all software devices in a single panel
- Redesigned notifications

* Wed Nov 13 2019 Matej Marusak <mmarusak@redhat.com> - 206-1
- Machines: Network interface deletion
- Machines: Refactor Create VM dialog and introduce a download option
- Software Updates: Use notifications for available updates info
- Machines: Configure read-only and shareable disks (rhbz#1684304)
- machines: Implement adding virtual network interfaces (rhbz#1672753)
- Machines: Creation of Storage Volumes (rhbz#1676506)
- Machines: VM creation and import dialog changes
- Machines: Enable interface type "direct" in NIC configuration
- Machines: LVM storage pools (rhbz#1676600)
- Machines: VM creation dialog now shows the recommended memory for the selected OS
- Machines: Managing of Virtual Networks (rhbz#1672755)
- Machines: Support more disk types

* Mon Sep 09 2019 Martin Pitt <mpitt@redhat.com> - 197.3-1
- Machines: Fix race condition with handling *EVENT_UNDEFINED (rhbz#1715388)

* Tue Aug 13 2019 Martin Pitt <mpitt@redhat.com> - 197.2-1
- Machines: Stop bringing libvirt package as a dependency (rhbz#1728219)
- Machines: Implement VM installation for additional disk types
- Machines: Fix setting of volume format when adding new disks to VMs (rhbz#1732303)
- Machines: Disallow pool deletion if pool/volumes are used by any VM (rhbz#1731865)
- Check for subscription only if enabled in package manager (rhbz#1701067)

* Thu Aug 01 2019 Martin Pitt <mpitt@redhat.com> - 197.1-1
- Machines: Fix crash on deleting VM in the middle of the installation (rhbz#1715399)
- Machines: Properly refresh storage pools (rhbz#1680293)
- Machines: Fix pool types which don't support volume creation (rhbz#1731849)
- Machines: Disable PXE booting on session connection (rhbz#1731803)

* Thu Jun 27 2019 Martin Pitt <mpitt@redhat.com> - 197-1
- Machines: Support all storage pool types for new disks
- Machines: Show available space on host at VM creation
- Machines: Fix regression on network tab rhbz#1720267

* Thu Jun 13 2019 Martin Pitt <mpitt@redhat.com> - 196-1
- Machines: Support ISO source from http:// rhbz#1644267
- Machines: Select destination storage pool on creation rhbz#1658852
- Machines: Hide iscsi-direct type from create new pool dialog when not
  available rhbz#1709708
- Machines: Fix handling of storage pools that failed to get active
  rhbz#1715388
- Machines: Fix OS detection while changing installation source rhbz#1715409

* Sun May 05 2019 Martin Pitt <mpitt@redhat.com> - 193-1
- Machines: iSCSI direct storage pools
- Machines: Auto-detect guest operating system rhbz#1652959
- Machines: Support https://*.iso installation source rhbz#1684422
- Machines: Fix crash on VM creation with Edge browser rhbz#1692707
- Storage: The "Format" button is no longer hidden
- Storage: Improve performance with many block devices

* Thu Apr 04 2019 Martin Pitt <mpitt@redhat.com> - 191-1
- Storage: Fix pre-filling of vdo fstab options rhbz#1672935
- Machines: Add PXE boot rhbz#1680973
- Machines: Add pause/resume rhbz#1680401
- Machines: Configure boot device order rhbz#1672760
- Machines: Import existing qcow2 image rhbz#1666825
- Machines: Edit virtual memory rhbz#1676557
- Machines: Deletion of storage volumes rhbz#1668882

* Wed Mar 13 2019 Martin Pitt <mpitt@redhat.com> - 189-1
- Machines: Remove useless notifications from disk tab rhbz#1632800
- Machines: Add deletion and deactivation of storage pools/volumes
  rhbz#1658847, rhbz#1668882, rhbz#1668877
- Machines: Fix preparation of disk data for disks of type volume rhbz#1661897
- Machines: Add disk format field when creating new disk xml rhbz#1662213
- Machines: Fix storage pool state after destroy/undefine rhbz#1663793
- Machines: Add import of existing images rhbz#1666825
- Machines: Enable/disable VM autostart rhbz#1670491

* Wed Jan 23 2019 Martin Pitt <mpitt@redhat.com> - 184.1-1
- storage: Always round dialog size slider input rhbz#1665955

* Fri Dec 14 2018 Martin Pitt <mpitt@redhat.com> - 184-1
- Machines: Fix Dialog and tab layouts rhbz#1658490, rhbz#1657119
- Machines: Fix information popup in vCPU dialog rhbz#1657133
- Machines: Enforce https:// URLs for remote VM image locations rhbz#1644267
- Storage: Filesystem labels are validated upfront rhbz#1655580
- Storage: Some mount options are prefilled when needed
- Storage: Fix empty tooltips rhbz#1655922

* Wed Nov 28 2018 Martin Pitt <mpitt@redhat.com> - 183-1
- Machines: Manage storage pools
- Machines: libvirt connection choice during VM creation
- PackageKit page: Display registration status clearly
- Drop .map files from -tests, should be only in debuginfo package rhbz#1648953

* Mon Nov 12 2018 Martin Pitt <mpitt@redhat.com> - 181-1
- Fix key typing in file auto complete widget rhbz#1637866
- Use libvirt-dbus by default rhbz#1637803

* Fri Oct 12 2018 Martin Pitt <mpitt@redhat.com> - 180-1
- Machines: Show error messages in the correct place rhbz#1637811

* Thu Oct 04 2018 Martin Pitt <mpitt@redhat.com> - 179-1
- Fix building with platform-python rhbz#1631174
- Machines: Fix system VMs with non-root users rhbz#1632772
- Machines: Offer cockpit-machines as Application

* Wed Sep 19 2018 Martin Pitt <mpitt@redhat.com> - 178-1
- Storage: Fix URL parsing when showing tang-show-key advise rhbz#1631175

* Wed Sep 5 2018 Martin Pitt <mpitt@redhat.com> - 177-1
- Storage: Support LUKS v2 rhbz#1622834
- PackageKit: Install auto-updates backend on demand

* Wed Aug 8 2018 Marius Vollmer <mvollmer@redhat.com> - 175-1
- Storage: Network bound disk encryption
- cockpit-ostree is now in its own source package

* Thu Aug 2 2018 marius Vollmer <mvollmer@redhat.com> - 174-1
- Kubernetes: VM detail page
- Realmd: Install on demand
- firewalld service is now being dropped by upstream
- iscsi works fully now

* Wed Jul 25 2018 Martin Pitt <mpitt@redhat.com> - 173-1
- Storage: Offer installation of VDO
- Machines: Add disks to a virtual machine
- Disable cockpit-docker rhbz#1602951

* Wed Jul 11 2018 Martin Pitt <martin@piware.de> - 172-1

- System: Offer installation of PCP
- Software Updates: Improve layout in mobile mode
- Remove ability to drop privileges from navigation bar
- API: Introduce flow control for all channels
- Python 3 support

* Wed Jun 27 2018 Martin Pitt <martin@piware.de> - 171-1

- Machines: Add virtual CPU configuration
- Kubernetes: Add KubeVirt pod metrics
- Docker: Show container volumes
- Fix broken actions for non-administrators
- Networking: Handle non-running NetworkManager
- Accounts: User role improvements
- Localize times

* Wed Jun 13 2018 Martin Pitt <martin@piware.de> - 170-1

- Software Updates: Layout rework
- oVirt: Use authenticated libvirt connection by default
- Split out optional packages into new cockpit-appstream dist-git, see
  discussion in RHELPLAN-3661; append "+as" version suffix to avoid collisions
  with cockpit revisions.
- Temporarily disable cockpit-kubernetes rhbz#1584155

* Wed May 30 2018 Martin Pitt <martin@piware.de> - 169-1

- Storage: Offer installation of NFS client support
- System: Request FreeIPA SSL certificate for Cockpit's web server
- Services: Show unit relationships
- Provide motd help about how to access cockpit

* Wed May 16 2018 Martin Pitt <martin@piware.de> - 168-1

- Improve checks for root privilege availability

* Wed May 02 2018 Martin Pitt <martin@piware.de> - 167-1

- Networking: Add Firewall Configuration
- Kubernetes: Show Kubevirt Registry Disks

* Wed Apr 18 2018 Martin Pitt <martin@piware.de> - 166-1

- Kubernetes: Add creation of Virtual Machines
- Realms: Automatically set up Kerberos keytab for Cockpit web server
- Numbers now get formatted correctly for the selected language

* Wed Apr 04 2018 Martin Pitt <martin@piware.de> - 165-1

- Storage: Show more details of sessions and services that keep NFS busy
- Machines: Detect if libvirtd is not running
- Machines: Show virtual machines that are being created

* Wed Mar 21 2018 Martin Pitt <martin@piware.de> - 164-1

- Storage: Move NFS management into new details page
- System: Show available package updates and missing registration
- System: Fix inconsistent tooltips
- Logs: Change severities to officially defined syslog levels
- Machines: Add error notifications
- Accessibility improvements
- Reloading the page in the browser now reloads Cockpit package manifests

* Wed Mar 07 2018 Martin Pitt <martin@piware.de> - 163-1

- Drop "Transfer data asynchronously" VDO option on Storage page
- Hide Docker storage pool reset button when it cannot work properly
- Update jQuery to version 3.3.1 (deprecated cockpit API!)

* Fri Feb 09 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 161-2
- Escape macros in %%changelog

* Wed Feb 07 2018 Martin Pitt <martin@piware.de> - 161-1

- New VMs can be created on Machines page
- VMs running in Kubernetes can now be deleted
- Improve LVM volume resizing
- Add new Hardware Information page
- Load Application metadata (Appstream) packages on demand on Debian/Ubuntu
- Rename cockpit-ovirt package to cockpit-machines-ovirt
- Stop advertising and supporting cockpit-bundled jQuery library

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 160-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Wed Jan 24 2018 Martin Pitt <martin@piware.de> - 160-1

- Add kubevirt Virtual Machines overview
- Redesign package list on Software Updates page and show RHEL Errata
- Install AppStream collection metadata packages on demand on Apps page
- Add AppStream metadata to cockpit-sosreport for showing up on Apps page
- Change CPU graphs to use "100%%" for a fully loaded multi-processor system
- Show storage, network, and other numbers with 3 digits of precision
- Add an example bastion container

* Sat Jan 20 2018 Björn Esser <besser82@fedoraproject.org> - 159-2
- Rebuilt for switch to libxcrypt

* Wed Jan 10 2018 Martin Pitt <martin@piware.de> - 159-1

- Configure data deduplication with VDO devices on Storage page
- Add serial console to virtual Machines page and redesign the Consoles tab
- Show more error message details for failures on virtual Machines page

* Wed Dec 13 2017 Martin Pitt <martin@piware.de> - 158-1

- Add check boxes for common NFS mount options
- Clarify Software Update status if only security updates are available
- Create self-signed certificates with SubjectAltName

* Thu Nov 30 2017 Martin Pitt <martin@piware.de> - 157-1

- Add Networks tab to overview on Machines page
- The Apps page now displays SVG app icons

* Thu Nov 16 2017 Martin Pitt <martin@piware.de> - 156-1

- Redesign navigation and support mobile browsing
- Use /etc/cockpit/krb5.keytab if present to support alternate keytabs
- Add project homepage link to Apps page
- Maintain issue(5) file with current Cockpit status
- Use event-driven refresh of oVirt data instead of polling

* Tue Nov 07 2017 Martin Pitt <martin@piware.de> - 155-1

- Add NFS client support to the Storage page
- Add "Maintenance" switch for oVirt hosts
- Fix Terminal rendering issues in Chrome
- Prevent closing Terminal with Ctrl+W when focused
- Support the upcoming OpenShift 3.7 release

* Wed Oct 18 2017 Martin Pitt <martin@piware.de> - 154-1

- Center the "Disconnected" message in the content area
- Fix two layout regressions on the Cluster page
- Remove long-obsolete "./configure --branding" option

* Tue Oct 17 2017 Martin Pitt <martin@piware.de> - 153-1

- Add cockpit-ovirt package to control oVirt virtual machine clusters
- Clean up rpmlint/lintian errors in the packages

* Fri Oct 06 2017 Martin Pitt <martin@piware.de> - 152-1

- Add Applications page
- Add automatic update configuration for dnf to Software Updates
- Fix cockpit-bridge crash if /etc/os-release does not exist

* Mon Sep 25 2017 Stef Walter <stefw@redhat.com> - 151-2
- Add simulated test failure

* Thu Sep 21 2017 Martin Pitt <martin@piware.de> - 151-1

- Support loading SSH keys from arbitrary paths
- Support X-Forwarded-Proto HTTP header for Kubernetes
- Fix Kubernetes connection hangs (regression in version 150)

* Fri Sep 08 2017 Martin Pitt <martin@piware.de> - 150-1

- Automatically enable and start newly created timers on the Services page
- Support cockpit-dashboard installation into OSTree overlay on Atomic
- Support Kubernetes basic auth with Google Compute Engine 1.7.x

* Mon Aug 21 2017 petervo <petervo@redhat.com> - 149-1
- Support sending non-maskable interrupt to VMs
- Fix building on fedora 27
- Add information about non-met conditions for systemd services
- Clear cockpit cookie on logout

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 146-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 146-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Jul 21 2017 Martin Pitt <martin@piware.de> - 146-1

- Show recent updates and live update log on Software Updates page
- Improve available Software Updates table layout for small/mobile screens
- Support OAuth Kubernetes logins to work with Google Compute Engine
- Fix reporting ABRT crashes that are already known to the server
- Scroll the virtual machine VNC console into view automatically

* Fri Jul 07 2017 Martin Pitt <martin@piware.de> - 145-1

- Resize the terminal dynamically to use all available space
- Let the Machines page update immediately after changes
- Add delete VM functionality to the Machines page
- Retire support for external Machines provider API
- Always recommend rebooting after applying Software Updates
- Group D-Bus channels to avoid hitting connection limits
- Fix building on Fedora Rawhide/glibc 2.25.90

* Mon Jun 19 2017 Martin Pitt <<martin@piware.de>> - 143-1

- Add "Software Updates" page for package (rpm/deb) based operating systems
- Fix cockpit-machines package to make inline VNC console actually work
- Fix Kubernetes authentication when Kubernetes configured for RBAC
- Build Docker page for s390x architecture

* Fri Jun 09 2017 Martin Pitt <<martin@piware.de>> - 142-1

- Virtual machines display an interactive console, either in browser, or a popup viewer
- Fix Virtual Machines operations on non-English locales
- Add documentation explaining how to grant/restrict access via polkit rules

* Fri Apr 21 2017 Martin Pitt <<mpitt@redhat.com>> - 139-1

- Show more information about virtual machines, such as boot order
- Fix enablement of timer systemd units created on Services page
- Fix Storage crash on multiple iSCSI sessions
- cockpit-docker is now installable with docker-ce or other alternatives
- Hide docker push commands on Registry image pages for  "pull" roles

* Mon Apr 10 2017 Stef Walter <<stefw@redhat.com>> - 138-1
- Only allow mdraid disk removal when it won't destroy data
- Allow DN style usernames in the Kubernetes dashboard
- Simplify protocol that cockpit talks to session authentication processes

* Thu Mar 30 2017 Martin Pitt <<mpitt@redhat.com>> - 137-1

- Read ~/.ssh/known_hosts for connecting to remote machines with ssh
- The Storage LVM setup can add unpartitioned free space as a physical volume
- NetworkManager's Team plugin can be used on architectures other than x86_64
- Cockpit's web server understands and properly responds to HTTP HEAD requests
- Allow parameter substitution in manifest when spawning peer bridges

* Thu Mar 09 2017 Martin Pitt <<mpitt@redhat.com>> - 134-1

- Show /etc/motd in the "System" task page
- Drop "System" service actions which are intended for scripts
- Make login page translatable
- NetworkManager now activates slave interfaces by itself
- Add call timeout option to the cockpit.dbus() API
- The Debian packaging is now able to apply binary patches

* Thu Mar 02 2017 Martin Pitt <<mpitt@redhat.com>> - 133-1

- Remotely managed machines are now configured in /etc/cockpit/machines.d/*.json
- Fix NetworkManager's "MTU" dialog layout
- Build the cockpit-tests package for releases too
- Split translations into individual packages
- Packages now configure alternate cockpit-bridge's to interact with the system

* Thu Feb 23 2017 Martin Pitt <<mpitt@redhat.com>> - 132-1

- Make basic SELinux functionality available without setroubleshootd
- Allow changing the MAC address for ethernet adapters and see them for bonds
- Hide "autoconnect" checkbox for network devices without settings
- Support for external providers other than libvirt on Machines page
- Some tooltip fixes
- Add option to restrict max read size to the Cockpit file API
- Relax dependencies on cockpit-bridge package on Debian/Ubuntu
- Rename cockpit-test-assets package to cockpit-tests
- When touching patched files handle case of only one file
- Always build the cockpit-tests subpackage

* Mon Feb 06 2017 Stef Walter <<stefw@redhat.com>> - 131-1
- Show session virtual machines on Machines page
- Fix use of the TAB key on login page
- Robust naming and detection of network bond master
- Debian packaging fixes

* Wed Jan 25 2017 Stef Walter <<stefw@redhat.com>> - 130-1
- cockpit.file() can read non-memory-mappable file
- Add kdump configuration user interface
- Allow container Registry Console user names with '@' sign

* Wed Jan 18 2017 Stef Walter <<stefw@redhat.com>> - 129-1
- Diagnostic sosreport feature now works on RHEL Atomic again
- The configure script has a --disable-ssh option to toggle libssh dep
- The configure --disable-ws option has been replaced with above.
- Unit tests have been fixed on recent GLib versions
- Several Fedora and Debian packaging fixes

* Wed Dec 14 2016 Stef Walter <<stefw@redhat.com>> - 126-1
- Show security scan information about containers
- Choose whether password is cached and reused on login screen
- Allow renaming of active devices in networking interface
- More clearly indicate when checking network connectivity
- The remotectl command can now combine certificate and key files
- Support Openshift's certificate autogeneration when used as a pod
- The remotectl tool now checks for keys in certificate files
- Domain join operations can now be properly cancelled
- Make Kerberos authentication work even if gss-proxy is in use
- Javascript code can now export DBus interfaces
- When proxied, support X-Forwarded-Proto
- Ignore block devices with a zero size in the storage interface

* Thu Nov 24 2016 Stef Walter <<stefw@redhat.com>> - 125-1
- Cockpit is now properly translatable
- Display OSTree signatures
- New expandable views for storage devices
- No longer offer to format read-only block devices
- Use stored passphrases for LUKS devices properly
- Start testing on RHEL 7.3
- More strict about transport channels a bridge accepts
- System shutdown can be scheduled by date

* Wed Nov 16 2016 Stef Walter <<stefw@redhat.com>> - 124-1
- Build and test on Debian Jessie
- Deprecate older javascript files
- Properly terminate user sessions on the Accounts page
- Fix regression on login screen in older Internet Explorer browsers
- Fix regression where Date Picker was not shown in System Time dialog

* Thu Nov 10 2016 Stef Walter <<stefw@redhat.com>> - 123-1
- Release a second tarball with cached javascript dependencies
- Start verifying that Cockpit works on Ubuntu 16.04
- Enable and verify the network functionality on Debian
- Integration tests now log core dumps for diagnosis

* Tue Nov 01 2016 Stef Walter <stefw@redhat.com> - 122-1
- Works with UDisks in addition to storaged
- Allow logging into other systems from login page
- Explicitly specify javascript dependency versions

* Fri Oct 28 2016 Stef Walter <stefw@redhat.com> - 121-1
- Network Manager Checkpoints
- Add Debian Branding
- Fix GSSAPI login on Debian and Ubuntu
- Generate map files for debugging Javascript and CSS

* Sat Oct 22 2016 Stef Walter <stefw@redhat.com> - 120-1
- New containers page layout
- Quick filtering of containers and images on the container page
- Added sidebar for phisical volumes in a volume group
- Run a separate cockpit-ssh process when making SSH connections
- Allow connecting to remote machines from the login page
- Only connect to remote machines already known to Cockpit
- Fix bugs preventing journal page from working on Firefox 49
- Add tooltip describing group name in Roles list

* Sat Oct 01 2016 Dennis Gilmore <dennis@ausil.us> - 119-2
- enabled cockpit-docker on aarch64, ppc64, ppc64le

* Thu Sep 29 2016 petervo <petervo@redhat.com> - 119-1
- Adds basic VM Management and Monitoring
- MDRaid job improvements
- Show unmanaged network devices
- Better errors when formating storage devices
- Updated VNC example
- Port subscriptions package to react
- Allow branding.css to overide shell css

* Wed Sep 07 2016 Stef Walter <stefw@redhat.com> - 118-1
- Support PAM conversations on the Login screen
- Users can create systemd timer jobs
- Provide default names for volume groups and logical volumes
- Make Docker graphs work on Debian
- Only offer to format disks with supported file systems
- Show all managed NetworkManager devices
- Use webpack for building Cockpit javascript
- Cockpit URLs can be proxied with a configured HTTP path prefix
- Allow Cockpit packages to require a minimum version of Cockpit
- Translations fixes

* Thu Aug 11 2016 Stef Walter <stefw@redhat.com> - 0.117-1
- * Add support for network teams
- * Select translations for complex language names
- * Don't allow formating extended partitions
- * Can configure Openshift Registry so anonymous users can pull images

* Fri Jul 29 2016 Stef Walter <stefw@redhat.com> - 0.116-1
- * Support for volumes when starting a docker container
- * Support for setting environment variables in a docker container
- * Fix regressions that broke display of localized text

* Thu Jul 21 2016 Stef Walter <stefw@redhat.com> - 0.115-1
- * Setup Docker container and image storage through the UI
- * Use Webpack to build Cockpit UI packages
- * Update the Cockpit Vagrant development box to use Fedora 24

* Tue Jul 12 2016 Stef Walter <stefw@redhat.com> - 0.114-1
- .104
- * Network configuration of the Ethernet MTU
- * Red Hat Subscriptions can now specify activation keys and orgs
- * Start integration testing on CentOS
- * SSH Host keys are show on system page
- * Machine ID is shown on system page
- * Show intelligent password score error messages

* Thu Jul 07 2016 Stef Walter <stefw@redhat.com> - 0.113-1
- * Show timer information for systemd timer jobs
- * Use 'active-backup' as the default for new network bonds
- * When changing system time check formats properly
- * Hide the machine asset tag when no asset exists
- * Disable the network on/off switch for unknown or unmanaged interfaces
- * Show full string for system hardware info and operating system name

* Wed Jun 29 2016 Stef Walter <stefw@redhat.com> - 0.112-1
- * Don't show network interfaces where NM_CONTROLLED=no is set
- * Add textual fields to container memory and CPU sliders
- * Display contianer memory and CPU resources on Debian
- * Disable tuned correctly when clearing a performance profile
- * Fix SELinux enforcing toggle switch and status

* Tue Jun 21 2016 Stef Walter <stefw@redhat.com> - 0.111-1
- * Tarball build issue in 0.110 is now fixed
- * The Containers page layouts have been tweaked
- * Make the Containers resource limits work again
- * Registry image now have layers displayed correctly

* Thu Jun 02 2016 Dominik Perpeet <dperpeet@redhat.com> - 0.109-1
- * API stabilization, structural cleanup
- * SELinux Troubleshooting: documentation, support latest API
- * Update Patternfly
- * Use CockpitLang cookie and Accept-Language for localization
- * Can now click through to perform administration tasks on Nodes on the Cluster dashboard
- * Cockpit terminal now supports shells like fish

* Fri May 27 2016 Stef Walter <stefw@redhat.com> - 0.108-1
- * SELinux troubleshooting alerts can now be dismissed
- * Show SELinux icon for critical alerts
- * SELinux enforcing mode can be turned off and on with a switch
- * Kubernetes Nodes are now include charts about usage data
- * Fix Debian dependency on Docker
- * Update the look and feel of the toggle switch
- * Update ListenStream documentation to include address info

* Fri May 20 2016 Stef Walter <stefw@redhat.com> - 0.107-1
- * Display image stream import errors
- * Add GlusterFS persistent volumes in Cluster dashboard
- * Show a list of pending persistent volume claims
- * jQuery Flot library is no longer part of the base1 package
- * Fix Content-Security-Policy issues with jQuery Flot

* Thu May 12 2016 Stef Walter <stefw@redhat.com> - 0.106-1
- * Add namespaces to cockpit CSS classes
- * Display container image layers in a simpler graph
- * Hide actions in Cluster projects listing that are not accessible

* Wed May 04 2016 Stef Walter <stefw@redhat.com> - 0.105-1
- * Strict Content-Security-Policy in all shipped components of Cockpit
- * Can now add and remove Openshift users to and from groups
- * Add timeout setting for Cockpit authentication
- * Registry interface now has checkbox for mirroring from insecure registries
- * Kubernetes dashboard now allows deletion of Nodes

* Thu Apr 28 2016 Stef Walter <stefw@redhat.com> - 0.104-1
- * Show errors correctly when deleting or modifying user accounts
- * Add support for iSCSI cluster volumes
- * Strict Content-Security-Policy in the dashboard, sosreport and realmd code
- * Better list expansion and navigation behavior across Cockpit
- * Don't show 'Computer OU' field when leaving a domain
- * Remove usage of bootstrap-select
- * Show errors properly in performance profile dialog
- * Fix Cluster sidebar to react to window size
- * Allow specifying specific tags in registry image streams
- * Make registry project access policy more visible

* Tue Apr 19 2016 Stef Walter <stefw@redhat.com> - 0.103-1
- * Strict Content-Security-Policy for subscriptions component
- * New dialog for Kubernetes connection configuration
- * Release to a cockpit-project Ubuntu PPA
- * Remove jQuery usage from cockpit.js
- * New styling for cluster dashboard
- * Fix build issue on MIPS

* Thu Apr 14 2016 Stef Walter <stefw@redhat.com> - 0.102-1
- * Can configure Docker restart policy for new containers
- * Use a single dialog for creating logical volumes
- * Package and test the storage UI on Debian
- * Don't offer 'Computer OU' when joining IPA domains
- * Don't distribute jshint build dependency due to its non-free license

* Fri Feb 12 2016 Stef Walter <stefw@redhat.com> - 0.95-1
- * iSCSI initiator support on the storage page
- * Page browser title now uses on operating system name
- * Better look when Cockpit disconnects from the server
- * Avoid use of NFS in the Vagrantfile
- * Expand 'Tools' menu when navigating to one of its items
- * Set a default $PATH in cockpit-bridge

* Tue Feb 02 2016 Stef Walter <stefw@redhat.com> - 0.94-1
- * Handle interruptions during cockpit-ws start while reading from /dev/urandom
- * Remove BIOS display from Server Summary page
- * Support tuned descriptions
- * Fix Content-Security-Policy in example manifest.json files

* Mon Jan 25 2016 Stef Walter <stefw@redhat.com> - 0.93-1
- * Set system performance profile via tuned
- * Support for WebSocket client in cockpit-bridge
- * Support using Nulecule with Openshift
- * Actually exit cockpit-ws when it's idle

* Wed Jan 20 2016 Stef Walter <stefw@redhat.com> - 0.92-1
- * OAuth login support
- * Update Patternfly
- * Log to stderr when no journal
- * Make sosreport work on RHEL and Atomic

* Thu Jan 14 2016 Stef Walter <stefw@redhat.com> - 0.91-1
- * Fix computing of graph samples on 32-bit OS
- * Distribute licenses of included components
- * Distribute development dependencies
- * Support 'make clean' properly in the tarball

* Tue Jan 05 2016 Stef Walter <stefw@redhat.com> - 0.90-1
- * Fix Content-Security-Policy which broke loading in certain situations
- * Deal correctly with failures trying to join unsupported domains
- * Add documentation about Cockpit startup
- * Better data in storage usage graphs
- * Start creating debian source packages

* Tue Dec 22 2015 Stef Walter <stefw@redhat.com> - 0.89-1
- * Start routine testing of Cockpit on Debian Unstable
- * Make the config file case insensitive
- * Reorder graphs on server summary page
- * Don't suggest syncing users when adding a machine to dashboard
- * Enable weak dependencies for F24+
- * Show correct data in per interface network graphs
- * Fix the Vagrantfile to pull in latest Cockpit
- * Add Content-Security-Policy header support

* Fri Dec 18 2015 Stef Walter <stefw@redhat.com> - 0.88-1
- * User interface for OSTree upgrades and rollbacks
- * General reusable purpose angular kubernetes client code
- * Allow custom login scripts for handling authentication
- * A specific dashboards can now be the default destination after login
- * Kill ssh-agent correctly when launched by cockpit-bridge
- * Add a new cockpit-stub bridge for non-local access

* Thu Dec 10 2015 Stef Walter <stefw@redhat.com> - 0.87-1
- * Fix login on Windows, don't prompt for additional auth
- * Use the machine host name in the default self-signed certificate
- * Cockpit release tarballs are now distributed in tar-ustar format
- * Allow overriding package manifests
- * Testing and build fixes

* Fri Dec 04 2015 Stef Walter <stefw@redhat.com> - 0.86-1
- * SOS report UI page
- * Simpler way for contributors to build cockpit RPMs
- * Infrastructure for implementing downloads

* Wed Nov 18 2015 Stef Walter <stefw@redhat.com> - 0.84-1
- * Add a cockpit manual page
- * Set correct SELinux context for certificates
- * Remove custom SELinux policy
- * Testing and bug fixes

* Tue Nov 03 2015 Stef Walter <stefw@redhat.com> - 0.83-1
- * Fix NTP server configuration bugs
- * Kubernetes dashboard topology icons don't leave the view
- * Kubernetes dashboard uses shared container-terminal component
- * Fix race when adding machine to Cockpit dashboard
- * Updated documentation for running new distributed tests
- * Lots of other bug and testing fixes

* Wed Oct 28 2015 Stef Walter <stefw@redhat.com> - 0.82-1
- * Support certificate chains properly in cockpit-ws
- * Rename the default self-signed certificate
- * Implement distributed integration testing

* Wed Oct 21 2015 Stef Walter <stefw@redhat.com> - 0.81-1
- * Allow configuring NTP servers when used with timesyncd
- * Fix regression in network configuration switches
- * Make the various graphs look better
- * Openshift Routes and Deployment Configs can be removed
- * Run integration tests using TAP "test anything protocol"
- * Lots of other bug fixes and cleanup

* Wed Oct 14 2015 Stef Walter <stefw@redhat.com> - 0.80-1
- * UI for loading, viewing, changing Private SSH Keys
- * Always start an ssh-agent in the cockpit login session
- * New listing panel designs
- * Lots of testing and bug fixes

* Wed Oct 07 2015 Stef Walter <stefw@redhat.com> - 0.79-1
- * Vagrant file for Cockpit development
- * Use libvirt for testing
- * Display only last lines of Kubernetes container logs

* Wed Sep 30 2015 Stef Walter <stefw@redhat.com> - 0.78-1
- * Fix extreme CPU usage issue in 0.77 release
- * Fix compatibility with older releases
- * Offer to activate multipathd for multipath disks
- * Guide now contains insight into feature internals
- * Lots of other minor bug fixes

* Wed Sep 23 2015 Marcin Juszkiewicz <mjuszkiewicz@redhat.com> - 0.77-1.1
- disable FMA support to get it pass all tests on secondary architectures
- removed duplicated "global rel 1"

* Tue Sep 22 2015 Stef Walter <stefw@redhat.com> - 0.77-1
- * Work better with multipath storage
- * Deletion of kubernetes objects
- * Cleaner URLs in the bookmark bar
- * Show a warning when adding too many machines
- * Make authentication work when embedding Cockpit
- * Complete componentizing Cockpit

* Wed Sep 16 2015 Stef Walter <stefw@redhat.com> - 0.76-1
- * Fix displaying of network bonds
- * Better Kubernetes filter bar, shell access
- * Show some Openshift related objects
- * Use patternfly v2.2

* Thu Sep 10 2015 petervo <petervo@redhat.com> - 0.75-1
- New design for kubernetes listing pages
- Namespace filter for kubernetes
- Pretty http error pages
- Lots of bugs, build and testing fixes

* Thu Sep 03 2015 Stef Walter <stefw@redhat.com> - 0.74-1
- * Display an intelligent message when password auth is not possible
- * Correctly start terminal in home directory
- * NetworkManager code is in a separate package
- * PCP is an optional build dependency
- * Lots of bugs, build and testing fixes

* Wed Aug 26 2015 Stef Walter <stefw@redhat.com> - 0.73-1
- * Kubernetes UI can connect to non-local API server
- * Automate Web Service container build on Docker Hub
- * Add validation options to TLS client connections
- * PAM pam_ssh_add.so module for loading SSH keys based on login password
- * Build, testing and other fixes

* Mon Aug 17 2015 Peter <petervo@redhat.com> - 0.71-1
- Update to 0.71 release.

* Wed Aug 12 2015 Stef Walter <stefw@redhat.com> - 0.70-1
- Depend on kubernetes-client instead of kubernetes
- Update to 0.70 release.

* Thu Aug 06 2015 Stef Walter <stefw@redhat.com> - 0.69-1
- Update to 0.69 release.

* Wed Jul 29 2015 Peter <petervo@redhat.com> - 0.68-1
- Update to 0.68 release.

* Thu Jul 23 2015 Peter <petervo@redhat.com> - 0.66-1
- Update to 0.66 release

* Fri Jul 17 2015 Peter <petervo@redhat.com> - 0.65-2
- Require libssh 0.7.1 on fedora >= 22 systems

* Wed Jul 15 2015 Peter <petervo@redhat.com> - 0.65-1
- Update to 0.65 release

* Wed Jul 08 2015 Peter <petervo@redhat.com> - 0.64-1
- Update to 0.64 release

* Wed Jul 01 2015 Peter <petervo@redhat.com> - 0.63-1
- Update to 0.63 release
- Remove cockpit-docker for armv7hl while docker
  packages are being fixed

* Thu Jun 25 2015 Peter <petervo@redhat.com> - 0.62-1
- Update to 0.62 release

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.61-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed Jun 10 2015 Peter <petervo@redhat.com> - 0.61-1
- Update to 0.61 release

* Mon Jun 01 2015 Stef Walter <stefw@redhat.com> - 0.60-1
- Update to 0.60 release

* Wed May 27 2015 Peter <petervo@redhat.com> - 0.59-1
- Update to 0.59 release

* Fri May 22 2015 Peter <petervo@redhat.com> - 0.58-1
- Update to 0.58 release

* Wed May 20 2015 Peter <petervo@redhat.com> - 0.57-1
- Update to 0.57 release

* Wed May 13 2015 Peter <petervo@redhat.com> - 0.56-1
- Update to 0.56 release

* Wed May 06 2015 Stef Walter <stefw@redhat.com> - 0.55-1
- Update to 0.55 release

* Fri Apr 24 2015 Peter <petervo@redhat.com> - 0.54-1
- Update to 0.54 release

* Tue Apr 21 2015 Peter <petervo@redhat.com> - 0.53-1
- Update to 0.53 release

* Thu Apr 16 2015 Stef Walter <stefw@redhat.com> - 0.52-1
- Update to 0.52 release

* Tue Apr 14 2015 Peter <petervo@redhat.com> - 0.51-1
- Update to 0.51 release

* Tue Apr 07 2015 Stef Walter <stefw@redhat.com> - 0.50-1
- Update to 0.50 release

* Wed Apr 01 2015 Stephen Gallagher <sgallagh@redhat.com> 0.49-2
- Fix incorrect Obsoletes: of cockpit-daemon

* Wed Apr 01 2015 Peter <petervo@redhat.com> - 0.49-1
- Update to 0.49 release.
- cockpitd was renamed to cockpit-wrapper the cockpit-daemon
  package was removed and is now installed with the
  cockpit-bridge package.

* Mon Mar 30 2015 Peter <petervo@redhat.com> - 0.48-1
- Update to 0.48 release

* Mon Mar 30 2015 Stephen Gallagher <sgallagh@redhat.com> 0.47-2
- Don't attempt to build cockpit-kubernetes on armv7hl

* Fri Mar 27 2015 Peter <petervo@redhat.com> - 0.47-1
- Update to 0.47 release, build docker on armvrhl

* Thu Mar 26 2015 Stef Walter <stefw@redhat.com> - 0.46-1
- Update to 0.46 release

* Mon Mar 23 2015 Stef Walter <stefw@redhat.com> - 0.45-1
- Update to 0.45 release

* Sat Mar 21 2015 Stef Walter <stefw@redhat.com> - 0.44-3
- Add back debuginfo files to the right place

* Fri Mar 20 2015 Stef Walter <stefw@redhat.com> - 0.44-2
- Disable separate debuginfo for now: build failure

* Fri Mar 20 2015 Stef Walter <stefw@redhat.com> - 0.44-1
- Update to 0.44 release

* Thu Mar 19 2015 Stef Walter <stefw@redhat.com> - 0.43-2
- Don't break EPEL or CentOS builds due to missing branding

* Wed Mar 18 2015 Stef Walter <stefw@redhat.com> - 0.43-1
- Update to 0.43 release

* Tue Mar 17 2015 Stef Walter <stefw@redhat.com> - 0.42-2
- Fix obseleting cockpit-assets

* Sat Mar 14 2015 Stef Walter <stefw@redhat.com> - 0.42-1
- Update to 0.42 release

* Wed Mar 04 2015 Stef Walter <stefw@redhat.com> - 0.41-1
- Update to 0.41 release

* Thu Feb 26 2015 Stef Walter <stefw@redhat.com> - 0.40-1
- Update to 0.40 release

* Thu Feb 19 2015 Stef Walter <stefw@redhat.com> - 0.39-1
- Update to 0.39 release

* Wed Jan 28 2015 Stef Walter <stefw@redhat.com> - 0.38-1
- Update to 0.38 release

* Thu Jan 22 2015 Stef Walter <stefw@redhat.com> - 0.37-1
- Update to 0.37 release

* Mon Jan 12 2015 Stef Walter <stefw@redhat.com> - 0.36-1
- Update to 0.36 release

* Mon Dec 15 2014 Stef Walter <stefw@redhat.com> - 0.35-1
- Update to 0.35 release

* Thu Dec 11 2014 Stef Walter <stefw@redhat.com> - 0.34-1
- Update to 0.34 release

* Fri Dec 05 2014 Stef Walter <stefw@redhat.com> - 0.33-3
- Only depend on docker stuff on x86_64

* Fri Dec 05 2014 Stef Walter <stefw@redhat.com> - 0.33-2
- Only build docker stuff on x86_64

* Wed Dec 03 2014 Stef Walter <stefw@redhat.com> - 0.33-1
- Update to 0.33 release

* Mon Nov 24 2014 Stef Walter <stefw@redhat.com> - 0.32-1
- Update to 0.32 release

* Fri Nov 14 2014 Stef Walter <stefw@redhat.com> - 0.31-1
- Update to 0.31 release

* Wed Nov 12 2014 Stef Walter <stefw@redhat.com> - 0.30-1
- Update to 0.30 release
- Split Cockpit into various sub packages

* Wed Nov 05 2014 Stef Walter <stefw@redhat.com> - 0.29-3
- Don't require test-assets from selinux-policy
- Other minor tweaks and fixes

* Wed Nov 05 2014 Stef Walter <stefw@redhat.com> - 0.29-2
- Include selinux policy as a dep where required

* Wed Nov 05 2014 Stef Walter <stefw@redhat.com> - 0.29-1
- Update to 0.29 release

* Thu Oct 16 2014 Stef Walter <stefw@redhat.com> - 0.28-1
- Update to 0.28 release
- cockpit-agent was renamed to cockpit-bridge

* Fri Oct 10 2014 Stef Walter <stefw@redhat.com> - 0.27-1
- Update to 0.27 release
- Don't create cockpit-*-admin groups rhbz#1145135
- Fix user management for non-root users rhbz#1140562
- Fix 'out of memory' error during ssh auth rhbz#1142282

* Wed Oct 08 2014 Stef Walter <stefw@redhat.com> - 0.26-1
- Update to 0.26 release
- Can see disk usage on storage page rhbz#1142459
- Better order for lists of block devices rhbz#1142443
- Setting container memory limit fixed rhbz#1142362
- Can create storage volume of maximum capacity rhbz#1142259
- Fix RAID device Bitmap enable/disable error rhbz#1142248
- Docker page connects to right machine rhbz#1142229
- Clear the format dialog label correctly rhbz#1142228
- No 'Drop Privileges' item in menu for root rhbz#1142197
- Don't flash 'Server has closed Connection on logout rhbz#1142175
- Non-root users can manipulate user accounts rhbz#1142154
- Fix strange error message when editing user accounts rhbz#1142154

* Wed Sep 24 2014 Stef Walter <stefw@redhat.com> - 0.25-1
- Update to 0.25 release

* Wed Sep 17 2014 Stef Walter <stefw@redhat.com> - 0.24-1
- Update to 0.24 release

* Wed Sep 10 2014 Stef Walter <stefw@redhat.com> - 0.23-1
- Update to 0.23 release

* Wed Sep 03 2014 Stef Walter <stefw@redhat.com> - 0.22-1
- Update to 0.22 release

* Tue Aug 26 2014 Patrick Uiterwijk <puiterwijk@redhat.com> - 0.21-1
- Update to 0.21 release

* Sat Aug 16 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.20-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Aug 14 2014 Stef Walter <stefw@redhat.com> 0.20-1
- Update to 0.20 release

* Thu Aug 07 2014 Stef Walter <stefw@redhat.com> 0.19-1
- Update to 0.19 release

* Wed Jul 30 2014 Stef Walter <stefw@redhat.com> 0.18-1
- Update to 0.18 release
- Add glib-networking build requirement
- Let selinux-policy-targetted distribute selinux policy

* Mon Jul 28 2014 Colin Walters <walters@verbum.org> 0.17-2
- Drop Requires and references to dead test-assets subpackage

* Thu Jul 24 2014 Stef Walter <stefw@redhat.com> 0.17-1
- Update to 0.17 release

* Wed Jul 23 2014 Stef Walter <stefw@redhat.com> 0.16-3
- Distribute our own selinux policy rhbz#1110758

* Tue Jul 22 2014 Stef Walter <stefw@redhat.com> 0.16-2
- Refer to cockpit.socket in scriptlets rhbz#1110764

* Thu Jul 17 2014 Stef Walter <stefw@redhat.com> 0.16-1
- Update to 0.16 release

* Thu Jul 10 2014 Stef Walter <stefw@redhat.com> 0.15-1
- Update to 0.15 release
- Put pam_reauthorize.so in the cockpit PAM stack

* Thu Jul 03 2014 Stef Walter <stefw@redhat.com> 0.14-1
- Update to 0.14 release

* Mon Jun 30 2014 Stef Walter <stefw@redhat.com> 0.13-1
- Update to 0.13 release

* Tue Jun 24 2014 Stef Walter <stefw@redhat.com> 0.12-1
- Update to upstream 0.12 release

* Fri Jun 20 2014 Stef Walter <stefw@redhat.com> 0.11-1
- Update to upstream 0.11 release

* Thu Jun 12 2014 Stef Walter <stefw@redhat.com> 0.10-1
- Update to upstream 0.10 release

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri May 23 2014 Stef Walter <stefw@redhat.com> 0.9-1
- Update to upstream 0.9 release
- Fix file attribute for cockpit-polkit

* Wed May 21 2014 Stef Walter <stefw@redhat.com> 0.8-1
- Update to upstream 0.8 release
- cockpitd now runs as a user session DBus service

* Mon May 19 2014 Stef Walter <stefw@redhat.com> 0.7-1
- Update to upstream 0.7 release

* Wed May 14 2014 Stef Walter <stefw@redhat.com> 0.6-1
- Update to upstream 0.6 release

* Tue Apr 15 2014 Stef Walter <stefw@redhat.com> 0.5-1
- Update to upstream 0.5 release

* Thu Apr 03 2014 Stef Walter <stefw@redhat.com> 0.4-1
- Update to upstream 0.4 release
- Lots of packaging cleanup and polish

* Fri Mar 28 2014 Stef Walter <stefw@redhat.com> 0.3-1
- Update to upstream 0.3 release

* Wed Feb 05 2014 Patrick Uiterwijk (LOCAL) <puiterwijk@redhat.com> - 0.2-0.4.20140204git5e1faad
- Redid the release tag

* Tue Feb 04 2014 Patrick Uiterwijk (LOCAL) <puiterwijk@redhat.com> - 0.2-0.3.5e1faadgit
- Fixed license tag
- Updated to new FSF address upstream
- Removing libgsystem before build
- Now claiming specific manpages
- Made the config files noreplace
- Removed the test assets
- Put the web assets in a subpackage

* Tue Feb 04 2014 Patrick Uiterwijk (LOCAL) <puiterwijk@redhat.com> - 0.2-0.2.5e1faadgit
- Patch libgsystem out
