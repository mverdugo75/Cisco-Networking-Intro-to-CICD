from genie.testbed import load
from genie.utils.diff import Diff
import json
import os

# Load the testbed based on the GitHub Actions context
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

testbed_env = os.environ.get("TESTBED_ENV", "lab")  # Default to lab if not set

testbed_map = {
    "lab": "tests/testbed/lab_testbed.yaml",
    "prod": "tests/testbed/prod_testbed.yaml",
}

testbed_path = testbed_map.get(testbed_env)

if testbed_path is None:
    raise ValueError(f"Unknown TESTBED_ENV: '{testbed_env}'. Must be 'lab' or 'prod'.")

testbed = load(os.path.join(BASE_DIR, testbed_path))

with open("pre_snapshot.json") as f:
    pre_snapshot = json.load(f)

issues_found = False

for device_name, device in testbed.devices.items():
    device.connect(log_stdout=False)

    post_state = {
        "interfaces": device.parse("show ip interface brief"),
        "vlans": device.parse("show vlan brief"),
    }

    device.disconnect()

    # Diff pre vs post
    diff = Diff(pre_snapshot[device_name], post_state)
    diff.findDiff()

    if diff.diffs:
        print(f"\n[{device_name}] Changes detected:")
        print(diff)
        issues_found = True
    else:
        print(f"[{device_name}] No unexpected changes. ✓")

if issues_found:
    exit(1)  # Fails the pipeline stage
