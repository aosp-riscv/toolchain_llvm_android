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
# pylint: disable=invalid-name
"""Script to submit builds/tests in Forrest."""

from typing import Dict, List, NamedTuple
import re
import yaml

import test_paths
import utils

USER = utils.check_output(['whoami']).strip()

changeSpecsPB = """
    change_specs {{
      gerrit_change {{
        hostname: "android"
        change_number: {cl_number}
      }}
    }}"""

buildRequestPB = """
build_request {{
  pending_build {{
    branch: "{branch}"
    target: "{target}"
    {change_specs}
    force_cherry_pick: true
    exclude_submitted_together_changes: true
  }}
}}
"""

testRequestPB = """
test_request {{
  atp_test {{
    test_name: "{test_name}"
  }}
  runner: TRADEFED
  device_selection {{
    test_bench {{
      cluster: "{cluster}"
      run_target: "{run_target}"
    }}
  }}
  run_count: 1
  shard_count: 1
  location: REMOTE
  branch_gcl: ""
  test_bench_gcl: "{gcl_path}/{test_bench_gcl}"
  test_run_context: ""
  import_extra_args: true
}}
"""

suffixFields = """
user: "{user}@google.com"
tag: "{tag}"
"""


class ClusterRecord(NamedTuple):
    """Device info needed to submit a test on Forrest."""
    cluster: str
    run_target: str
    test_bench_gcl: str


def _readClusterInfo() -> Dict[str, ClusterRecord]:
    with open(test_paths.CLUSTER_INFO_YAML) as infile:
        info = yaml.load(infile, Loader=yaml.FullLoader)
        return {
            device: ClusterRecord(**record) for device, record in info.items()
        }


ClusterInfo = _readClusterInfo()


def _get_device_info(target: str) -> ClusterRecord:
    matches = [d for d in ClusterInfo if d in target]
    if len(matches) == 0:
        raise RuntimeError(
            f'No match for {target} in {test_paths.CLUSTER_INFO_YAML}')
    if len(matches) > 1:
        raise RuntimeError(
            f'Multiple matches for {target} in {test_paths.CLUSTER_INFO_YAML}: '
            + str(matches))
    return ClusterInfo[matches[0]]


def invokeForrestRun(branch: str, target: str, cl_numbers: List[str],
                     tests: List[str], tag: str) -> str:
    """Submit a build/test to forrest."""
    gcl_path = test_paths.gcl_path()
    if tests:
        cluster_info = _get_device_info(target)._asdict()

    # Create Forrest protobuf and write to file.
    pb = ''
    changeSpecs = '\n'.join(
        changeSpecsPB.format(cl_number=cl) for cl in cl_numbers)
    pb += buildRequestPB.format(
        branch=branch, target=target, change_specs=changeSpecs)

    for test in tests:
        pb += testRequestPB.format(
            test_name=test, gcl_path=gcl_path, **cluster_info)
    pb += suffixFields.format(user=USER, tag=tag)

    cl_str = '_'.join(cl_numbers)
    pbFile = f'/tmp/forrest_{tag}_{branch}_{target}_{cl_str}.pb'
    # TODO(pirama): Cleanup files in /tmp.  They are currently retained to help
    # debugging.
    with open(pbFile, 'w') as fileobj:
        fileobj.write(pb)

    # Submit to forrest and return invocation id.
    output = utils.check_output([test_paths.FORREST, 'run', pbFile])
    match = re.search(r'http://go/forrest-run/(L[0-9]*)\x1b', output)
    if not match:
        raise RuntimeError('Forrest invocation id not found in output,' +
                           f'which is\n{output}\n<END_OF_FORREST_OUTPUT>')
    return match.group(1)
