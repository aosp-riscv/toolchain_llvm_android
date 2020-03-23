#
# Copyright (C) 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""APIs for accessing toolchains."""

from pathlib import Path

import constants
import functools
import hosts
import paths
import version

class Toolchain:
    """Base toolchain."""

    cc: Path  # pylint: disable=invalid-name
    cxx: Path
    lib_dir: Path
    path: Path

    def get_resource_dir(self, arch: str = '') -> Path:
        raise NotImplementedError()


class _HostToolchain(Toolchain):
    """Base toolchain that compiles host binary."""

    @property
    def cc(self) -> Path:  # type: ignore
        return self.path / 'bin' / 'clang'

    @property
    def cxx(self) -> Path:  # type: ignore
        return self.path / 'bin' / 'clang++'

    @property
    def lib_dir(self) -> Path:  # type: ignore
        return self.path / 'lib64'

    @property
    def _version_file(self) -> Path:  # type: ignore
        return self.path / 'include' / 'clang' / 'Basic'/ 'Version.inc'

    @property
    def _version(self) -> version.Version:
        return version.Version(self._version_file)

    def get_resource_dir(self, arch: str = '') -> Path:
        return (self.lib_dir / 'clang' / self._version.long_version() /
                'lib' / 'linux' / arch)


def _clang_prebuilt_path(host: hosts.Host) -> Path:
    """Returns the path to prebuilt clang toolchain."""
    return (paths.ANDROID_DIR / 'prebuilts' / 'clang' / 'host' /
            host.os_tag / constants.CLANG_PREBUILT_VERSION)


def build_toolchain_for_path(path: Path) -> Toolchain:
    toolchain = _HostToolchain()
    toolchain.path = path
    return toolchain


def get_prebuilt_toolchain() -> Toolchain:
    return build_toolchain_for_path(_clang_prebuilt_path(hosts.build_host()))
