#!/usr/bin/env python3

import logging
import os
import re

ORIG_ENV = dict(os.environ)

import android_version
import base_builders
import builders
import paths
import utils

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
        'KYTHE_CORPUS': "https://android.googlesource.com/toolchain/llvm-project/",
    }

    extractor = utils.subprocess_run([str(paths.KYTHE_RUN_EXTRACTOR),
        'compdb',
        f'-extractor={paths.KYTHE_CXX_EXTRACTOR}',
        f'-path={json}'],
        env=env,
        capture_output=True)

    # sanity check that runextractor fails in an expected fashion.
    if extractor.returncode == 0:
        raise RuntimeError("runextractor is expected to fail")

    relative_path = lambda full_path: full_path[len(str(paths.ANDROID_DIR))+1:]
    srcs = re.findall('(?P<file>\S+)\': error running extractor',
                      extractor.stderr)
    srcSet = set(relative_path(f) for f in srcs)
    if srcSet != EXPECTED_ERRORS:
        print(extractor.stderr)
        raise RuntimeError('Runextractor failures different than expected' +\
                           f'Expected: {EXPECTED_ERRORS}\n' +\
                           f'Actual: {srcSet}\n')


def package():
    kythe_out_dir = paths.KYTHE_OUTPUT_DIR
    tar_cwd, tar_files = kythe_out_dir.parent, kythe_out_dir.name

    dist_dir = ORIG_ENV.get('DIST_DIR', utils.out_path())
    package_name = os.path.join(dist_dir, 'kythe-corpous.tar.gz')
    tar = ['tar', '-czC', tar_cwd, '-f', package_name, tar_files]
    utils.check_call(tar)


def main():
    logging.basicConfig(level=logging.INFO)

    builder = build_llvm()
    build_kythe_corpus(builder)
    package()

if __name__ == '__main__':
    main()
