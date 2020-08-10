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

import functools
from pathlib import Path
from typing import Optional

from builder_registry import BuilderRegistry
import paths
import version

class Toolchain:
    """Base toolchain."""

    path: Path
    build_path: Path

    def __init__(self, path: Path, build_path: Path) -> None:
        self.path = path
        self.build_path = build_path

    @property
    def cc(self) -> Path:  # pylint: disable=invalid-name
        """Returns the path to c compiler."""
        return self.path / 'bin' / 'clang'

    @property
    def cxx(self) -> Path:
        """Returns the path to c++ compiler."""
        return self.path / 'bin' / 'clang++'

    @property
    def cl(self) -> Path:
        """Returns the path to windows c++ compiler."""
        return self.path / 'bin' / 'clang-cl'

    @property
    def ar(self) -> Path:
        """Returns the path to llvm-ar."""
        return self.path / 'bin' / 'llvm-ar'

    @property
    def rc(self) -> Path:
        """
        Returns the path to MinGW windres.
        llvm-rc is not feature complete yet.
        """
        return paths.MINGW_ROOT / 'bin' / 'x86_64-w64-mingw32-windres'

    @property
    def ranlib(self) -> Path:
        """Returns the path to llvm-ranlib."""
        return self.path / 'bin' / 'llvm-ranlib'

    @property
    def addr2line(self) -> Path:
        """Returns the path to llvm-addr2line."""
        return self.path / 'bin' / 'llvm-addr2line'

    @property
    def nm(self) -> Path:
        """Returns the path to llvm-nm."""
        return self.path / 'bin' / 'llvm-nm'

    @property
    def objcopy(self) -> Path:
        """Returns the path to llvm-objcopy."""
        return self.path / 'bin' / 'llvm-objcopy'

    @property
    def objdump(self) -> Path:
        """Returns the path to llvm-objdump."""
        return self.path / 'bin' / 'llvm-objdump'

    @property
    def readelf(self) -> Path:
        """Returns the path to llvm-readelf."""
        return self.path / 'bin' / 'llvm-readelf'

    @property
    def mt(self) -> Path:
        """Returns the path to llvm-mt."""
        return self.path / 'bin' / 'llvm-mt'

    @property
    def strip(self) -> Path:
        """Returns the path to llvm-strip."""
        return self.path / 'bin' / 'llvm-strip'

    @property
    def lib_dir(self) -> Path:
        """Returns the path to lib dir."""
        return self.path / 'lib64'

    @property
    def _version_file(self) -> Path:
        return self.path / 'include' / 'clang' / 'Basic'/ 'Version.inc'

    @functools.cached_property
    def _version(self) -> version.Version:
        return version.Version(self._version_file)

    @property
    def clang_lib_dir(self) -> Path:
        return self.lib_dir / 'clang' / self._version.long_version()

    @property
    def resource_dir(self) -> Path:
        return self.clang_lib_dir / 'lib' / 'linux'


@functools.lru_cache
def _build_toolchain_for_path(path: Path, build_path: Path) -> Toolchain:
    """Returns a toolchain object for a given path."""
    return Toolchain(path, build_path)


def get_prebuilt_toolchain() -> Toolchain:
    """Returns the prebuilt toolchain."""
    # Prebuilt toolchain doesn't have a build path. Use a temp path instead.
    return _build_toolchain_for_path(paths.CLANG_PREBUILT_DIR, Path('.'))


def get_toolchain_from_builder(builder) -> Toolchain:
    """Gets the toolchain from a toolchain builder."""
    return _build_toolchain_for_path(builder.install_dir, builder.output_dir)


def get_toolchain_by_name(name: str) -> Toolchain:
    """Tet a toolchain by name."""
    if name == 'prebuilt':
        return get_prebuilt_toolchain()
    return get_toolchain_from_builder(BuilderRegistry.get(name))


_RUNTIME_TOOLCHAIN: Toolchain = get_prebuilt_toolchain()
def set_runtime_toolchain(toolchain: Toolchain) -> None:
    """Sets the toolchain used to build runtime."""
    global _RUNTIME_TOOLCHAIN  # pylint: disable=global-statement
    _RUNTIME_TOOLCHAIN = toolchain


def get_runtime_toolchain() -> Toolchain:
    """Gets the toolchain used to build runtime."""
    global _RUNTIME_TOOLCHAIN  # pylint: disable=global-statement
    return _RUNTIME_TOOLCHAIN

_OUTPUT_TOOLCHAIN: Optional[Toolchain] = None
def set_output_toolchain(toolchain: Toolchain) -> None:
    """Set the Linux toolchain being built.  Used by builders to install
    additional artifacts.
    """
    global _OUTPUT_TOOLCHAIN
    if _OUTPUT_TOOLCHAIN is not None:
        raise RuntimeError('Cannot change output toolchain')
    _OUTPUT_TOOLCHAIN = toolchain

def get_output_toolchain() -> Toolchain:
    """Get the Linux toolchain being built.  Used by builders to install
    additional artifacts.
    """
    if _OUTPUT_TOOLCHAIN is None:
        raise RuntimeError('Output toolchain is not set yet.')
    return _OUTPUT_TOOLCHAIN
