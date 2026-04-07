from genie.testbed import load
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

snapshot = {}

for device_name, device in testbed.devices.items():
    device.connect(log_stdout=False)

    # Capture structured state
    snapshot[device_name] = {
        "interfaces": device.parse("show ip interface brief"),
        "vlans": device.parse("show vlan brief"),
    }

    device.disconnect()

# Save snapshot to file (passed as artifact to post-check)
with open("pre_snapshot.json", "w") as f:
    json.dump(snapshot, f, indent=2)

print(f"Pre-check complete. Snapshot saved. (Testbed: {testbed_env})")
