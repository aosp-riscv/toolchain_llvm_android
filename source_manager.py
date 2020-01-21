#!/usr/bin/env python
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

"""
Package to manage LLVM sources when building a toolchain.
"""

import os
import shutil
import subprocess

import android_version
import utils


def apply_patches(source_dir, svn_version, patch_json, patch_dir):
    """Apply patches in $patch_dir/$patch_json to $source_dir.

    Invokes external/toolchain-utils/llvm_tools/patch_manager.py to apply the
    patches.
    """

    patch_manager_cmd = [
        utils.android_path('prebuilts', 'build-tools', 'linux-x86', 'bin',
                           'py3-cmd'),
        utils.android_path('external', 'toolchain-utils', 'llvm_tools',
                          'patch_manager.py'),
        # Python3 prebuilts in prebuilts/build-tools has an issue with argument
        # parsing and ignores the first argument.  Pass a dummy argument until
        # the issue is fixed.
        'blah',
        '--svn_version', svn_version,
        '--patch_metadata_file', patch_json,
        '--filesdir_path', patch_dir,
        '--src_path', source_dir,
        '--use_src_head', 'true',
        '--failure_mode', 'fail'
    ]

    # py3-cmd in prebuilts/build-tools doesn't seem to add the current script's
    # directory to sys.path.  Explicitly pass the path in PYTHONPATH
    env = dict(os.environ)
    env['PYTHONPATH'] = os.path.join('external', 'toolchain-utils',
                                     'llvm_tools')
    subprocess.check_call(patch_manager_cmd, env=env)


def _get_svn_version_to_build(build_llvm_next):
    if build_llvm_next:
        rev = android_version.svn_revision_next
    else:
        rev = android_version.svn_revision
    return rev[1:] # strip the leading 'r'


def _same_llvm_dirs(dir1, dir2):
    diff_cmd = ['diff', '-r', dir1, dir2]

    # The libcxx test inputs have a symlink libcxx/test/**/bad_symlink that is
    # always reported as different by diff
    diff_cmd.extend(('-x', 'bad_symlink'))

    try:
        subprocess.check_call(diff_cmd)
    except subprocess.CalledProcessError:
        return False
    return True


def setup_sources(source_dir, build_llvm_next, patch_sources):
    """Setup toolchain sources into source_dir.

    Copies toolchain/llvm-project into source_dir.  If patch_sources is True,
    apply patches per the specification in
    toolchain/llvm_android/patches/PATCHES.json.  The function overwrites
    source_dir only if necessary to avoid recompiles during incremental builds.
    """

    copy_from = utils.android_path('toolchain', 'llvm-project')

    # Copy llvm source tree to a temporary directory.
    tmp_source_dir = source_dir.rstrip('/') + '.tmp'
    if os.path.exists(tmp_source_dir):
        utils.rm_tree(tmp_source_dir)
    shutil.copytree(copy_from, tmp_source_dir, symlinks=True)

    if patch_sources:
        patch_dir = utils.android_path('toolchain', 'llvm_android', 'patches')
        patch_json = os.path.join(patch_dir, 'PATCHES.json')
        svn_version = _get_svn_version_to_build(build_llvm_next)

        apply_patches(tmp_source_dir, svn_version, patch_json, patch_dir)

    # Copy tmp_source_dir to source_dir if they are different.  This avoids
    # invalidating prior build outputs.
    if not os.path.exists(source_dir):
        os.rename(tmp_source_dir, source_dir)
    elif not _same_llvm_dirs(tmp_source_dir, source_dir):
        utils.rm_tree(source_dir)
        os.rename(tmp_source_dir, source_dir)
