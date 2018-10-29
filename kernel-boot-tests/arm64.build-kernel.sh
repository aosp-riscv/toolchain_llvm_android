#!/bin/bash
# Usage: ./arm64.build-kernel.sh path/to/clang
set -ex

clang=$(readlink -f $1)

if [[ -d linux ]]; then
  cd linux
  git fetch origin --depth 1
  git checkout origin/master
else
  rm -rf linux
  git clone --depth 1 \
    git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
  cd linux
fi

ARCH=arm64 make CC=$clang defconfig
ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- make CC=$clang -j`nproc`
cd -
