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
from typing import List, Tuple

import configs
import hosts
import paths

class Toolchain:
    """Base toolchain."""

    @property
    def cc(self) -> Path:
        """The path to the c compiler."""
        raise NotImplementedError

    @property
    def cxx(self) -> Path:
        """The path to the cxx compiler."""
        raise NotImplementedError

    @property
    def flags(self) -> Tuple[List[str], List[str]]:
        """Returns cflags and ldflags."""
        raise NotImplementedError

    @property
    def sysroot(self) -> str:
        """Returns sysroot."""
        raise NotImplementedError


class HostToolchain(Toolchain):
    """Base toolchain that compiles host binary."""

    is_32_bit: bool = False

    def __init__(self, path: Path, host: hosts.Host) -> None:
        self.path = path
        self.host = host

    @property
    def cc(self) -> Path:
        """The path to the c compiler."""
        return self.path / 'bin' / 'clang'

    @property
    def cxx(self) -> Path:
        """The path to the cxx compiler."""
        return self.path / 'bin' / 'clang++'

    @property
    def _debug_prefix_flag(self) -> str:
        return '-fdebug-prefix-map={}='.format(paths.ANDROID_DIR)

    @property
    def flags(self) -> Tuple[List[str], List[str]]:
        cflags: List[str] = []
        ldflags: List[str] = []

        cflags.append(self._debug_prefix_flag)

        if self.host.is_darwin:
            return cflags, ldflags

        # GCC toolchain flags for Linux and Windows
        if self.host.is_linux:
            gcc_root = (paths.ANDROID_DIR / 'prebuilts' / 'gcc' / hosts.build_host().os_tag /
                        'host' / 'x86_64-linux-glibc2.17-4.8')
            gcc_triple = 'x86_64-linux'
            gcc_version = '4.8.3'

            # gcc-toolchain is only needed for Linux
            cflags.append(f'--gcc-toolchain={gcc_root}')
        elif self.host.is_windows:
            gcc_root = (paths.ANDROID_DIR / 'prebuilts' / 'gcc' / hosts.build_host().os_tag /
                        'host' / 'x86_64-w64-mingw32-4.8')
            gcc_triple = 'x86_64-w64-mingw32'
            gcc_version = '4.8.3'

        gcc_bin_dir = gcc_root / gcc_triple / 'bin'
        cflags.append(f'-B{gcc_bin_dir}')

        gcc_lib_dir = gcc_root / 'lib' / 'gcc' / gcc_triple / gcc_version
        if self.is_32_bit:
            gcc_lib_dir = gcc_lib_dir / '32'
            gcc_builtin_dir = gcc_root / gcc_triple / 'lib32'
        else:
            gcc_builtin_dir = gcc_root / gcc_triple / 'lib64'

        ldflags.append(f'-B{gcc_lib_dir}')
        ldflags.append(f'-L{gcc_lib_dir}')
        ldflags.append(f'-B{gcc_builtin_dir}')
        ldflags.append(f'-L{gcc_builtin_dir}')
        ldflags.append('-fuse-ld=lld')

        return cflags, ldflags

    @property
    def sysroot(self) -> str:
        if self.host.is_darwin:
            return ""
        return str(paths.ANDROID_DIR / 'prebuilts' / 'gcc' / hosts.build_host().os_tag /
                   'host' / 'x86_64-linux-glibc2.17-4.8' / 'sysroot')


class PrebuiltToolchain(HostToolchain):
    """A prebuilt toolchain used to build stage1."""

    def __init__(self) -> None:
        host = hosts.build_host()
        clang_path: Path = self.clang_prebuilt_path(host)
        super().__init__(clang_path, host=host)

    @staticmethod
    def clang_prebuilt_path(host: hosts.Host) -> Path:
        """Returns the path to prebuilt clang toolchain."""
        return (paths.ANDROID_DIR / 'prebuilts' / 'clang' / 'host' /
                host.os_tag / configs.CLANG_PREBUILT_VERSION)

    @property
    def flags(self) -> Tuple[List[str], List[str]]:
        cflags, ldflags = super().flags

        # Point CMake to the libc++.so from the prebuilts.  Install an rpath
        # to prevent linking with the newly-built libc++.so
        lib_dir = self.path / 'lib64'
        ldflags.append(f'-L{lib_dir}')
        ldflags.append(f'-Wl,-rpath,{lib_dir}')

        return (cflags, ldflags)
