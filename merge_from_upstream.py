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

import argparse
import os
import re
import subprocess
import sys

from utils import *


# A map of upstream commit sha to the computed llvm-svn number,
# to be used in parse_log.
SHA2REV = {
    '8ea148dc0cbff33ac3c80cf4273991465479a01e': 376048,
    '51adeae1c90c966f5ae7eb1aa8a380fcc7cd4806': 376784,
    '1549b4699a84838c3969590dc4f757b72f39f40d': 377024,
    '1689ad27af5c5712f42542807eb4ecdfe84c2eca': 377449,
    '7a2b704bf0cf65f9eb46fe3668a83b75aa2d80a6': 375681,
    'a3b22da4e0ea84ed5890063926b6f54685c23225': 377828,
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'revision', help='Revision number of llvm source.', type=int)
    parser.add_argument('sha', help='SHA string of llvm source.')
    parser.add_argument(
        '--create-new-branch',
        action='store_true',
        default=False,
        help='Create new branch using `repo start` before '
        'merging from upstream.')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Dry run, does not actually commit changes to local workspace.')
    return parser.parse_args()


def sync_upstream_branch(path):
    subprocess.check_call(['repo', 'sync', '.'], cwd=path)


def merge_projects(revision, sha, create_new_branch, dry_run):
    path = llvm_path()
    if not dry_run:
        sync_upstream_branch(path)
    if sha is None:
        raise LookupError('found no sha for %s.' % (revision))
    print('Project llvm-project git hash: %s' % sha)

    if create_new_branch:
        branch_name = 'merge-upstream-r%s' % revision
        check_call_d(['repo', 'start', branch_name, '.'],
                     cwd=path,
                     dry_run=dry_run)

    # Get the info since the last tag, the format is
    #   llvm-svn.[svn]-[number of changes since tag]-[sha of the current commit]
    desc = subprocess.check_output(
        ['git', 'describe', '--tags', '--long', '--match', 'llvm-svn.[0-9]*'],
        cwd=path,
        universal_newlines=True).strip()
    _, svnNum, numChanges, _ = desc.split('-')

    # Check changes since the previous merge point
    reapplyList = []
    print('Found %s changes since the last tag' % numChanges)
    hasUnknownPatch = False
    for i in range(int(numChanges) - 1, -1, -1):
        changeLog = subprocess.check_output([
            'git', 'show', 'HEAD~' + str(i), '--quiet', '--format=%h%x1f%B%x1e'
        ],
                                            cwd=path,
                                            universal_newlines=True)
        changeLog = changeLog.strip('\n\x1e')
        patchSha, patchRev, cherryPickSha  = parse_log(changeLog)
        if patchRev is None:
            if not cherryPickSha:
                print 'To reapply local change ' + patchSha
                reapplyList.append(patchSha)
            else:
                print('Unknown cherry pick, patchSha=%s cherryPickSha=%s'
                      % (patchSha, cherryPickSha))
                hasUnknownPatch = True
        else:
            if patchRev > revision:
                print 'To reapply ' + patchSha + ' ' + str(patchRev)
                reapplyList.append(patchSha)
            else:
                print 'To skip ' + patchSha + ' ' + str(patchRev)

    if hasUnknownPatch:
        print 'Abort, cannot merge with unknown patch!'
        sys.exit(1)

    # Reset to previous branch point, if necessary
    if int(numChanges) > 0:
        check_output_d([
            'git', 'revert', '--no-commit', '--no-merges',
            'llvm-' + svnNum + '...HEAD'
        ],
                       cwd=path,
                       dry_run=dry_run)
        check_output_d(
            ['git', 'commit', '-m revert to previous base llvm-' + svnNum],
            cwd=path,
            dry_run=dry_run)

    # Merge upstream revision
    check_call_d([
        'git', 'merge', '--quiet', sha, '-m',
        'Merge %s for LLVM update to %d' % (sha, revision)
    ],
                 cwd=path,
                 dry_run=dry_run)

    # Tag the merge point
    check_call_d(['git', 'tag', '-f', 'llvm-svn.' + str(revision)],
                 cwd=path,
                 dry_run=dry_run)

    # Reapply
    FNULL = open(os.devnull, 'w')
    for sha in reapplyList:
        subprocess.check_call(['git', '--no-pager', 'show', sha, '--quiet'],
                              cwd=path)

        # Check whether applying this change will cause conflict
        ret_code = subprocess.call(
            ['git', 'cherry-pick', '--no-commit', '--no-ff', sha],
            cwd=path,
            stdout=FNULL,
            stderr=FNULL)
        subprocess.check_call(['git', 'reset', '--hard'],
                              cwd=path,
                              stdout=FNULL,
                              stderr=FNULL)

        if ret_code != 0:
            print 'Change cannot merge cleanly, please manual merge if needed'
            print
            keep_going = yes_or_no('Continue?', default=False)
            if not keep_going:
                sys.exit(1)
            continue

        # Change can apply cleanly...
        reapply = yes_or_no('Reapply change?', default=True)
        if reapply:
            check_call_d(['git', 'cherry-pick', sha],
                         cwd=path,
                         stdout=FNULL,
                         stderr=FNULL,
                         dry_run=dry_run)
            # Now change the commit Change-Id.
            check_call_d(['git', 'commit', '--amend'],
                         cwd=path,
                         dry_run=dry_run)
        else:
            print 'Skipping ' + sha

        print


def parse_log(raw_log):
    log = raw_log.strip().split('\x1f')
    cherryPickSha = ''
    # Extract revision number from log data.
    foundRevision = 0
    for line in log[1].strip().split('\n'):
        tmp = re.search(r'^llvm-svn: (\d+)$', line)
        if tmp is not None:
            foundRevision = int(tmp.group(1))
        else:
            tmp = re.search(r'\(cherry picked from commit (.+)\)', line)
            if tmp is not None:
                cherryPickSha = tmp.group(1)
    if foundRevision:
        return (log[0], foundRevision, cherryPickSha)
    if cherryPickSha and cherryPickSha in SHA2REV:
        return (log[0], SHA2REV[cherryPickSha], cherryPickSha)
    return (log[0], None, cherryPickSha)


def main():
    args = parse_args()
    merge_projects(args.revision, args.sha, args.create_new_branch, args.dry_run)


if __name__ == '__main__':
    main()
