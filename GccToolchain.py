#!/usr/bin/env python
#
# Copyright (C) 2017 The Android Open Source Project
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

import utils

_gccRootPath = {
    ('arm', 'android')  : 'arm/arm-linux-androideabi-4.9/arm-linux-androideabi',
    ('arm64', 'android'): 'aarch64/aarch64-linux-android-4.9/aarch64-linux-android',
    ('x86_64', 'android'): 'x86/x86_64-linux-android-4.9/x86_64-linux-android',
    ('i386', 'android'): 'x86/x86_64-linux-android-4.9/x86_64-linux-android',
    ('mips', 'android'): 'mips/mips64el-linux-android-4.9/mips64el-linux-android',
    ('mips64', 'android'): 'mips/mips64el-linux-android-4.9/mips64el-linux-android',

    ('x86_64', 'linux'): 'host/x86_64-linux-glibc2.15-4.8/x86_64-linux',
    ('i686', 'linux'):  'host/x86_64-linux-glibc2.15-4.8/x86_64-linux',
}

class AndroidGccToolchain(object):
    def __init__(self, arch, os):
        self.os = os

        # normalize arch
        if arch in ('i686', 'i386', 'x86'):
            self.arch = 'i386'
        else:
            self.arch = arch

    def gccRoot(self):
        return utils.android_path('prebuilts/gcc', utils.build_os_type(),
                                  _gccRootPath((self.arch, self.os)))

    def bin(self):
        return os.path.join(self.gccRoot(), 'bin')

    def builtins(self):
        gccRoot = self.gccRoot()
        builtin_dir = os.path.join(gccRoot, '..', 'lib', 'gcc', os.path.basename(gccRoot),
                                '4.9.x')

        # 32-bit x86 and mips builtins are under the '32' subdir
        if self.arch == 'i386' or self.arch == 'mips':
            builtin_dir = os.path.join(builtin_dir, '32')

        return builtin_dir
