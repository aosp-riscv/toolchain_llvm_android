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

import global_configs
import hosts
import paths

class Toolchain:
    """Base toolchain."""

    @property
    def cc(self) -> Path:  # pylint: disable=invalid-name
        """The path to the c compiler."""
        raise NotImplementedError

    @property
    def cxx(self) -> Path:
        """The path to the cxx compiler."""
        raise NotImplementedError

    @property
    def lib_path(self) -> Path:
        """The path to toolchain libs."""
        raise NotImplementedError


class _HostToolchain(Toolchain):
    """Base toolchain that compiles host binary."""

    is_32_bit: bool = False

    def __init__(self, path: Path, host: hosts.Host) -> None:
        self.path = path
        self.host = host

    @property
    def cc(self) -> Path:
        return self.path / 'bin' / 'clang'

    @property
    def cxx(self) -> Path:
        return self.path / 'bin' / 'clang++'

    @property
    def lib_path(self) -> Path:
        return self.path / 'lib64'


class PrebuiltToolchain(_HostToolchain):
    """A prebuilt toolchain used to build stage1."""

    def __init__(self) -> None:
        host = hosts.build_host()
        clang_path: Path = self.clang_prebuilt_path(host)
        super().__init__(clang_path, host=host)

    @staticmethod
    def clang_prebuilt_path(host: hosts.Host) -> Path:
        """Returns the path to prebuilt clang toolchain."""
        return (paths.ANDROID_DIR / 'prebuilts' / 'clang' / 'host' /
                host.os_tag / global_configs.CLANG_PREBUILT_VERSION)
