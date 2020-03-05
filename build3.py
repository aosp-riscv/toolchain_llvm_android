#!/usr/bin/env python
#
# Copyright (C) 2018 The Android Open Source Project
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
"""Starts build.py with prebuilt python3."""

import os
import subprocess
import sys

THIS_DIR = os.path.realpath(os.path.dirname(__file__))
def get_host_tag():
    if sys.platform.startswith('linux'):
        return "linux-x86"
    elif sys.platform.startswith('darwin'):
        return "darwin-x86"
    else:
        raise RuntimeError('Unsupported host: {}'.format(sys.platform))


def main():
    python_bin = os.path.join(THIS_DIR, "..", "..", "prebuilts", "python", get_host_tag(), 'bin')
    python_bin = os.path.abspath(python_bin)
    os.environ['PATH'] = os.pathsep.join([python_bin, os.environ['PATH']])
    subprocess.check_call(
        ['python3', os.path.join(THIS_DIR, 'build.py')] + sys.argv[1:])


if __name__ == '__main__':
    main()

