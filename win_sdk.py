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
# pylint: disable=global-statement
"""Util functions for windows toolchain."""

from typing import Optional
from pathlib import Path

import paths
import utils

_WIN_SDK_PATH: Optional[Path] = None
_WIN_SDK_VER: Optional[str] = None


def _create_symlink(src_file: Path, new_name: str) -> None:
    if src_file.name == new_name:
        return

    symlink_path = src_file.parent / new_name
    if symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(src_file.name)


def _prepare() -> None:
    assert _WIN_SDK_PATH is not None
    assert _WIN_SDK_VER is not None

    header_dir = _WIN_SDK_PATH / 'Include' / _WIN_SDK_VER / 'um'
    for _file in header_dir.iterdir():
        _create_symlink(_file, _file.name.lower())

    lib_path = _WIN_SDK_PATH / 'Lib' / _WIN_SDK_VER / 'um' / 'x64'
    for _file in lib_path.iterdir():
        _create_symlink(_file, _file.name.lower())

    include_shared = _WIN_SDK_PATH / 'Include' / _WIN_SDK_VER / 'shared'
    _create_symlink(include_shared / 'driverspecs.h', 'DriverSpecs.h')
    _create_symlink(include_shared / 'specstrings.h', 'SpecStrings.h')
    _create_symlink(include_shared / 'WTypesbase.h', 'wtypesbase.h')


def set_path(path: Path) -> None:
    """Sets the path to a windows toolchain.
    A qualified package can be generated using the following script.
    https://chromium.googlesource.com/chromium/tools/depot_tools/+/refs/heads/master/win_toolchain/package_from_installed.py"""
    global _WIN_SDK_PATH, _WIN_SDK_VER
    _WIN_SDK_PATH = path
    _WIN_SDK_VER = next((path / 'Include').glob('*')).name
    _prepare()


def get_path() -> Optional[Path]:
    """Gets the path to windows toolchain."""
    return _WIN_SDK_PATH


def is_enabled() -> bool:
    """Whether windows toolchain is enabled."""
    return _WIN_SDK_PATH is not None


def download_and_enable() -> None:
    """(Google Internal Only) download and use msvc toolchain."""
    winsdk_path = paths.OUT_DIR / 'visualcpptools' / 'win_sdk'
    if winsdk_path.is_dir():
        return

    urls = [
        "sso://googleplex-android/platform/prebuilts/visualcpptools",
        "https://googleplex-android.googlesource.com/platform/prebuilts/visualcpptools",
    ]
    for url in urls:
        git_res = utils.subprocess_run(["git", "clone", "-b", "lldb-master-dev", "--depth=1", url], cwd=paths.OUT_DIR)
        if git_res.returncode == 0:
            set_path(paths.OUT_DIR / 'visualcpptools' / 'win_sdk')
            return
    raise RuntimeError('Failed to download windows sdk.')