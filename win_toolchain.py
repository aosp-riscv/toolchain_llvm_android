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
from typing import Optional
from pathlib import Path

_win_toolchain_path: Optional[Path] = None
_win_sdk_ver: Optional[str] = None
_prepared: bool = False


def _create_symlink(src_file: Path, new_name: str) -> None:
    if src_file.name == new_name:
        return

    symlink_path = src_file.parent / new_name
    if symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(src_file.name)


def _prepare() -> None:
    global _win_toolchain_path, _win_sdk_ver, _prepared
    if _prepared:
        return

    assert(_win_toolchain_path is not None)
    assert(_win_sdk_ver is not None)

    header_dir = _win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um'
    for f in header_dir.iterdir():
        _create_symlink(f, f.name.lower())

    lib_path = _win_toolchain_path / 'win_sdk' / 'Lib' / _win_sdk_ver / 'um' / 'x64'
    for f in lib_path.iterdir():
        _create_symlink(f, f.name.lower())
        
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um' / 'Windows.h', 'windows.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um' / 'WinBase.h', 'winbase.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um' / 'WinUser.h', 'winuser.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um' / 'WinNls.h', 'winnls.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'um' / 'Ole2.h', 'ole2.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'shared' / 'driverspecs.h', 'DriverSpecs.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'shared' / 'specstrings.h', 'SpecStrings.h')
    _create_symlink(_win_toolchain_path / 'win_sdk' / 'Include' / _win_sdk_ver / 'shared' / 'WTypesbase.h', 'wtypesbase.h')

    _prepared = True


def set_path(path: Path) -> None:
    global _win_toolchain_path, _win_sdk_ver, _prepared
    _win_toolchain_path = path
    _win_sdk_ver = next((path / 'win_sdk' / 'Include').glob('*')).name
    _prepared = False


def get_path() -> Optional[Path]:
    global _win_toolchain_path
    _prepare()
    return _win_toolchain_path


def is_enabled() -> bool:
    global _win_toolchain_path
    return _win_toolchain_path is not None


def download_and_enable() -> Path:
    return Path()
