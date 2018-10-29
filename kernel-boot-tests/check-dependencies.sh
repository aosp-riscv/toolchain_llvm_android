#!/bin/bash
set -exu

# Multiple invocations allow for easier debugging which command failed.
which qemu-system-aarch64
which timeout
which wget
which sha1sum
which unbuffer
