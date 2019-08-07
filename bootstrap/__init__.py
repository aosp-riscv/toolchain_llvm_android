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
"""Tools for bootstrapping Python 3."""
import datetime
import logging
import multiprocessing
import os
import pipes
import shutil
import subprocess
import sys
import timeit


THIS_DIR = os.path.realpath(os.path.dirname(__file__))


def logger():
    """Returns the module level logger."""
    return logging.getLogger(__name__)


def android_path(*args):
    """Returns the absolute path rooted within the top level source tree."""
    return os.path.normpath(os.path.join(THIS_DIR, '../../..', *args))


PYTHON_SOURCE = android_path('external/python/cpython3')


def _get_dir_from_env(default, env_var):
    """Returns the path to a directory specified by the environment.

    If the environment variable is not set, the default will be used. The
    directory is created if it does not exist.

    Args:
        default: The path used if the environment variable is not set.
        env_var: The environment variable that contains the path, if any.

    Returns:
        The absolute path to the directory.
    """
    path = os.path.realpath(os.getenv(env_var, default))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def get_out_dir():
    """Returns the out directory."""
    return _get_dir_from_env(android_path('out'), 'OUT_DIR')


def get_dist_dir():
    """Returns the distribution directory.

    The contents of the distribution directory are archived on the build
    servers. Suitable for build logs and final artifacts.
    """
    return _get_dir_from_env(os.path.join(get_out_dir(), 'dist'), 'DIST_DIR')


def path_in_out(dirname):
    """Returns a path within the out directory."

    Args:
        dirname: Name of the directory.

    Returns:
        Absolute path within the out directory.
    """
    return os.path.join(get_out_dir(), dirname)


def log_failure_and_exit(output):
    """Logs the bootstrapping failure and exits.

    Args:
        output: Output of the failed command.
    """
    log_dir = os.path.join(get_dist_dir(), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_path = os.path.join(log_dir, 'build_error.log')
    with open(log_path, 'w') as error_log:
        error_log.write('Bootstrapping failed!\n')
        error_log.write(output)

    logger().error(output)
    sys.exit('Bootstrapping failed!')


def check_output(cmd):
    """Logged version of subprocess.check_output.

    stderr is automatically forwarded to stdout.

    Args:
        cmd: argv style argument list for the process to be run.

    Returns:
        Output
    """
    logger().debug('Runnning: %s', ' '.join([pipes.quote(a) for a in cmd]))
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def build_python(install_dir, build_dir):
    """Builds and installs Python to the given directory.

    Args:
        install_dir: Install path for the built Python distribution.
        build_dir: Directory to use for building Python.
    """
    logger().info('Bootstrapping Python...')

    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    old_cwd = os.getcwd()
    try:
        os.chdir(build_dir)

        check_output([
            os.path.join(PYTHON_SOURCE, 'configure'),
            '--prefix=' + install_dir,

            # This enables PGO and requires running all the Python tests to
            # generate those profiles. If we end up repackaging this Python to
            # ship in the NDK we should do this, but for now it makes
            # bootstrapping take a lot longer and we don't need the perforance
            # since our build time is dominated by non-Python code anyway.
            # '--enable-optimizations',
        ])

        check_output([
            'make',
            '-j',
            str(multiprocessing.cpu_count()),
            'install',
        ])
    except subprocess.CalledProcessError as ex:
        log_failure_and_exit(ex.output)
    finally:
        os.chdir(old_cwd)


def install_requirements(install_dir, requirements):
    """Installs required Python packages using pip.

    Args:
        install_dir: Directory in which Python 3 is installed.
        requirements: Path to requirements.txt file to be passed to pip.
    """
    logger().info('Installing additional requirements...')
    try:
        check_output([
            os.path.join(install_dir, 'bin/pip3'),
            'install',
            '-r',
            requirements,
        ])
    except subprocess.CalledProcessError as ex:
        log_failure_and_exit(ex.output)


class Timer(object):  # pylint: disable=useless-object-inheritance
    """Execution timer.

    Can be used explicitly with stop/start, but preferably is used as a context
    manager:

    >>> timer = Timer()
    >>> with timer:
    >>>     do_something()
    >>> print('do_something() took {}'.format(timer.duration))
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None

    def start(self):
        """Start the timer."""
        self.start_time = timeit.default_timer()

    def finish(self):
        """Stop the timer."""
        self.end_time = timeit.default_timer()

        # Not interested in partial seconds at this scale.
        seconds = int(self.end_time - self.start_time)
        self.duration = datetime.timedelta(seconds=seconds)

    def __enter__(self):
        self.start()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.finish()


def read_requirements(requirements):
    """Returns the contents of a requirements file or None.

    Args:
        requirements: Path to a requirements.txt file that may or may not
        exist, or none.

    Returns:
        The contents of the requirements file if it exists, or None if the
        requirequirements file is None or does not exist.
    """

    if requirements is None:
        return None

    if not os.path.exists(requirements):
        return None

    with open(requirements) as requirements_file:
        return requirements_file.read()


class BootstrapManifest(object):  # pylint: disable=useless-object-inheritance
    """Describes the contents of the bootstrapped directory."""

    SOURCE_MANIFEST_PATH = os.path.join(PYTHON_SOURCE, 'README.rst')

    def __init__(self, install_path, requirements):
        self.install_path = install_path
        self.manifest_file = os.path.join(self.install_path, '.bootstrapped')

        self.requested_requirements_path = requirements
        self.bootstrapped_requirements_path = os.path.join(
            self.install_path, 'requirements.txt')

        self.requested_requirements = read_requirements(
            self.requested_requirements_path)
        self.bootstrapped_requirements = read_requirements(
            self.bootstrapped_requirements_path)

    def is_up_to_date(self):
        """Returns True if the bootstrap install is up to date."""
        if not os.path.exists(self.manifest_file):
            return False
        if not self.versions_match():
            logger().info('Bootstrap out of date: Python has changed.')
            return False
        if self.requested_requirements != self.bootstrapped_requirements:
            logger().info('Bootstrap out of date: requirements have changed.')
            return False
        return True

    def versions_match(self):
        """Returns True if the bootstrap has an up to date Python."""
        # Ideally this would be a check of the git revision of the Python
        # source, but we can't assume that information is available on the
        # build servers. For now, assume the README.rst will change for any
        # update. This should be fine since updates should include a change to
        # the version number.

        # This function should not be called if this file does not exist.
        assert os.path.exists(self.manifest_file)

        with open(self.SOURCE_MANIFEST_PATH) as readme_rst:
            source_manifest = readme_rst.read()
        with open(self.manifest_file) as manifest_file:
            bootstrapped_manifest = manifest_file.read()

        return source_manifest == bootstrapped_manifest

    def save(self):
        """Saves the bootstrap manifest to disk."""
        self.save_python_version()
        self.save_requirements()

    def save_python_version(self):
        shutil.copy2(self.SOURCE_MANIFEST_PATH, self.manifest_file)

    def save_requirements(self):
        if self.requested_requirements is not None:
            shutil.copy2(self.requested_requirements_path,
                         self.bootstrapped_requirements_path)
        # An existing bootstrap directory is removed if it needed to be
        # updated, so no need to remove an existing requirements file in the
        # case where a requirements file was used but no longer is.


def do_bootstrap(install_dir, requirements):
    """Helper function for bootstrapping.

    Builds and installs Python 3 if necessary, but does not modify the
    environment.

    Args:
        install_dir: Directory in which to install Python 3.
        requirements: An optional path to a requirements.txt file. This will be
            passed to pip to install additional dependencies. If None, no
            additional packages will be installed.

    Returns:
        Python 3 install directory.
    """
    build_dir = path_in_out('bootstrap-build')

    bootstrap_manifest = BootstrapManifest(install_dir, requirements)
    if bootstrap_manifest.is_up_to_date():
        return

    # If the bootstrap exists but is not up to date, purge it to ensure no
    # stale files remain.
    if os.path.exists(install_dir):
        shutil.rmtree(install_dir)

    timer = Timer()
    with timer:
        build_python(install_dir, build_dir)
        if requirements is not None:
            install_requirements(install_dir, requirements)
    logger().info('Bootstrapping completed in %s', timer.duration)

    bootstrap_manifest.save()


def bootstrap(requirements=None):
    """Creates a bootstrap Python 3 environment.

    Builds and installs Python 3 for use on the current host. After execution,
    the directory containing the python3 binary will be the first element in
    the PATH.

    Args:
        requirements: An optional path to a requirements.txt file. This will be
            passed to pip to install additional dependencies. If None, no
            additional packages will be installed.
    """
    install_dir = path_in_out('bootstrap')
    do_bootstrap(install_dir, requirements)
    bootstrap_bin = os.path.join(install_dir, 'bin')
    os.environ['PATH'] = os.pathsep.join([bootstrap_bin, os.environ['PATH']])
