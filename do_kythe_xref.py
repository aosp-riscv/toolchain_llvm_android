#!/usr/bin/env python3

import logging
import os
import re
import sys

import android_version
import builders
import hosts
import paths
import utils

ORIG_ENV = dict(os.environ)

def build_llvm() -> builders.Stage2Builder:
    builders.SwigBuilder().build()
    builders.LibEditBuilder().build()

    stage2 = builders.Stage2Builder()
    stage2.toolchain_name = 'prebuilt'
    stage2.build_name = 'stage2'
    stage2.svn_revision = android_version.get_svn_revision()

    # Differences from production toolchain:
    #   - sources are built directly from toolchain/llvm-project
    #   - built from prebuilt instead of a stage1 toolchain.
    #   - assertions enabled since some code is enabled only with assertions.
    #   - LTO is unnecessary.
    #   - extra targets so we get cross-references for more sources.
    stage2.src_dir = paths.ANDROID_DIR / 'toolchain' / 'llvm-project' / 'llvm'
    stage2.enable_assertions = True
    stage2.lto = False
    stage2.ninja_targets = ['all', 'UnitTests', 'google-benchmark-libcxx']
    stage2.build()
    return stage2

# runextractor is expected to fail on these sources.
EXPECTED_ERRORS = set([
    'toolchain/llvm-project/compiler-rt/lib/scudo/standalone/benchmarks/malloc_benchmark.cpp',
])

def build_kythe_corpus(builder: builders.Stage2Builder) -> None:
    kythe_out_dir = paths.KYTHE_OUTPUT_DIR
    if os.path.exists(paths.KYTHE_OUTPUT_DIR):
        utils.rm_tree(paths.KYTHE_OUTPUT_DIR)
    os.makedirs(paths.KYTHE_OUTPUT_DIR)

    json = builder.output_dir / 'compile_commands.json'
    env = {
        'KYTHE_OUTPUT_DIRECTORY': kythe_out_dir,
        'KYTHE_ROOT_DIRECTORY': paths.ANDROID_DIR,
        'KYTHE_CORPUS':
            'https://android.googlesource.com/toolchain/llvm-project/',
    }

    # Capture the output of runextractor and sanity check that it fails in an
    # expected fashion.
    extractor = utils.subprocess_run([str(paths.KYTHE_RUN_EXTRACTOR),
                                      'compdb',
                                      f'-extractor={paths.KYTHE_CXX_EXTRACTOR}',
                                      f'-path={json}'],
                                     env=env,
                                     capture_output=True)

    if extractor.returncode == 0:
        raise RuntimeError('runextractor is expected to fail')

    get_rel_path = lambda full_path: full_path[len(str(paths.ANDROID_DIR))+1:]
    failed_srcs = re.findall('(?P<file>\\S+)\': error running extractor',
                             extractor.stderr)
    srcSet = set(get_rel_path(f) for f in failed_srcs)
    if srcSet != EXPECTED_ERRORS:
        print(extractor.stderr)
        raise RuntimeError('Runextractor failures different than expected' +\
                           f'Expected: {EXPECTED_ERRORS}\n' +\
                           f'Actual: {srcSet}\n')


def package(build_name: str) -> None:
    # Build merge_kzips using soong
    utils.check_call(['build/soong/soong_ui.bash',
                      '--build-mode', '--all-modules',
                      f'--dir={paths.ANDROID_DIR}',
                      '-k', 'merge_zips'])
    merge_zips_path = utils.out_path('soong', 'host', hosts.build_host().os_tag,
                                     'bin', 'merge_zips')

    # Call: merge_zips $DIST_DIR/<build_name>.kzip <kzip files>
    output = os.path.join(ORIG_ENV.get('DIST_DIR', utils.out_path()),
                          build_name + '.kzip')

    kythe_out_dir = paths.KYTHE_OUTPUT_DIR
    kzip_files = [os.path.join(kythe_out_dir, kzip)
                  for kzip in os.listdir(kythe_out_dir)]

    utils.check_call([merge_zips_path, output] + kzip_files)


def main():
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 2:
        print(f'Usage: {sys.argv[0]} BUILD_NAME')
        sys.exit(1)
    build_name = sys.argv[1] if len(sys.argv) == 2 else 'dev'

    if not os.path.exists(utils.android_path('build', 'soong')):
        raise RuntimeError('build/soong does not exist.  ' +\
                           'Execute this script in master-plus-llvm branch.')

    builder = build_llvm()
    build_kythe_corpus(builder)
    package(build_name)


if __name__ == '__main__':
    main()
