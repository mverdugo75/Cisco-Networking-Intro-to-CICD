# Network Automation Workshop
## Lab Guide — Part 1: Ansible Fundamentals
This workshop covers a basic overview of Ansible for Cisco networking automation and change management.

Participant learning goals:
- Understand Ansible requirements, project structure, inventory, and vars
- Get started with ad-hoc commands and brownfield discovery
- Push configuration changes and explore advanced paths to pursue next

Approximate time: 1.5hr

## Section 1: Introduction to Ansible

### 1.1 What is Ansible?

> *Instructor: Brief conceptual overview — what problem does Ansible solve? Why do network engineers care?*

- Agentless automation — how it works over SSH/NETCONF
- Idempotency — what it means and why it matters in networking
- Key terms to know: **Control node**, **Managed nodes**, **Playbook**, **Task**, **Module**

### 1.2 Ansible Project Structure

> *Instructor: Walk through the folder layout students will be working with. Remind students that all work should be done inside the WSL filesystem — `~/ansible-cml/`*

```
ansible-cml
├── ansible.cfg
├── inventory
│   ├── digital-twin
│   │   ├── group_vars
│   │   │   └── all.yml
│   │   ├── hosts.ini
│   │   └── hosts.yaml
│   └── prod
│       ├── group_vars
│       │   └── all.yml
│       ├── hosts.ini
│       └── hosts.yaml
├── playbooks
│   ├── show_vlans.yml
│   └── verify_vlans.yml
├── roles
└── vars
    └── vlans.yml
```

Brief description of the purpose of each component:

- `ansible.cfg` — project-level configuration file
- `inventory/` — defines the devices Ansible will manage
- `vars/` and `group_vars/` — variable storage
- `playbooks/` — where automation logic lives


### 1.3 Inventory Deep Dive

Topics to cover:
- Defining hosts and groups
- INI vs YAML format
- Nested groups (`children`)

**Example PROD inventory:**

```yaml
# inventory/prod/hosts.yaml

all:
  children:
    network_devices:
      children:
        routers:
          hosts:
            PROD-RTR-11:
              ansible_host: 198.18.135.11
            PROD-RTR-12:
              ansible_host: 198.18.135.12
        switches_core:
          hosts:
            PROD-CORE-13:
              ansible_host: 198.18.135.13
            PROD-CORE-14:
              ansible_host: 198.18.135.14
        switches_access:
          hosts:
            PROD-ACC-15:
              ansible_host: 198.18.135.15
            PROD-ACC-16:
              ansible_host: 198.18.135.16
            PROD-ACC-17:
              ansible_host: 198.18.135.17
```

### 1.4 Variables
- Where to define credentials (vars vs group_vars vs vault)
- Common network variables: `ansible_network_os`, `ansible_connection`, `ansible_become`
- Brief mention of **Ansible Vault** for credential security (no deep dive needed)

**Example `prod/group_vars/cisco.yml`:**

```yaml
ansible_user: admin
ansible_password: "{{ vault_password }}"
ansible_network_os: cisco.ios.ios
ansible_connection: network_cli
ansible_become: yes
ansible_become_method: enable
```

### 1.5 `ansible.cfg` Walkthrough
Understand the key defaults used throughout the lab.

```ini
[defaults]
inventory = ./inventory/digital-twin/hosts.yaml
remote_user = admin
host_key_checking = False
```

---

## Section 2: Getting Started with Ansible

### 2.1 Your First Command — `ansible` Ad-Hoc

> *(Instructor: Show that Ansible can be used without a playbook for quick tasks)*

- Syntax: `ansible <host/group> -m <module> -a <args>`
- Run a ping against all devices to confirm connectivity

**Lab Task 2.1 — Ad-Hoc Ping:**

```bash
ansible all -m cisco.ios.ios_ping
```

> *(Instructor: Explain the difference between Ansible's `ping` module and ICMP ping. For network devices, use `cisco.ios.ios_ping` or simply confirm SSH connectivity.)*

### 2.2 Anatomy of a Playbook

> *(Instructor: Walk through each part of a basic playbook before running anything)*

- `hosts:` — which inventory targets to run against
- `gather_facts:` — typically disabled for network devices
- `tasks:` — ordered list of modules to execute
- `name:` — human-readable label for each task

**Example skeleton to walk through:**

```yaml
---
- name: My First Ansible Playbook
  hosts: routers
  gather_facts: no

  tasks:
    - name: Task description goes here
      cisco.ios.ios_command:
        commands:
          - show version
```

### 2.3 Brownfield Discovery — Mapping the Network

> *(Instructor: Frame this section — "You already have a network running. Let's use Ansible to document what's there.")*

Topics to cover:
- Using `cisco.ios.ios_command` to run `show` commands
- Capturing output with `register`
- Displaying output with `debug`

**Lab Task 2.2 — Gather Device Info:**

```yaml
---
- name: Brownfield Discovery
  hosts: all
  gather_facts: no

  tasks:
    - name: Gather device version info
      cisco.ios.ios_command:
        commands:
          - show version
          - show ip interface brief
          - show cdp neighbors detail
      register: discovery_output
    - name: Display output
      ansible.builtin.debug:
        var: discovery_output.stdout_lines
```

### 2.4 Structured Data with `ios_facts`

> *(Instructor: Show the difference between raw command output and structured facts)*

- Using `cisco.ios.ios_facts` to gather structured device data
- Why structured data matters for automation at scale

**Lab Task 2.3 — Gather Structured Facts:**

```yaml
---
- name: Gather IOS Facts
  hosts: all
  gather_facts: no

  tasks:
    - name: Collect device facts
      cisco.ios.ios_facts:
        gather_subset: all

    - name: Show hostname and IOS version
      ansible.builtin.debug:
        msg: "{{ ansible_net_hostname }} is running {{ ansible_net_version }}"
```

---

## Section 3: Pushing Changes with Ansible

> **Instructor Note:** Before this section, take a moment to reinforce idempotency. Remind students that a well-written playbook should be safe to run multiple times without causing unintended changes.

### 3.1 Making Changes Safely — `check` Mode

> *(Instructor: Show check mode before making any real changes — builds good habits)*

- What `--check` does and when to use it
- Its limitations on network devices (not all modules support it fully)

```bash
ansible-playbook playbooks/push_changes.yml --check
```

### 3.2 Lab Task — Updating Interface Descriptions

> *(Instructor: Good first change — highly visible, low risk, easy to verify)*

- Using `cisco.ios.ios_interfaces` to set interface descriptions
- Verifying the change with a follow-up `show` task

```yaml
---
- name: Update Interface Descriptions
  hosts: switches
  gather_facts: no

  tasks:
    - name: Set interface descriptions
      cisco.ios.ios_interfaces:
        config:
          - name: GigabitEthernet0/1
            description: "Uplink to Core"
          - name: GigabitEthernet0/2
            description: "Server Port"
        state: merged

    - name: Verify interface descriptions
      cisco.ios.ios_command:
        commands:
          - show interfaces description
      register: intf_output

    - name: Display result
      ansible.builtin.debug:
        var: intf_output.stdout_lines
```

### 3.3 Lab Task — Adding a VLAN

> *(Instructor: Slightly more impactful change — good for showing state management)*

- Using `cisco.ios.ios_vlans` to configure VLANs
- Explaining `state: merged` vs `state: replaced` vs `state: deleted`

```yaml
---
- name: Add VLANs to Switches
  hosts: switches
  gather_facts: no

  tasks:
    - name: Configure VLANs
      cisco.ios.ios_vlans:
        config:
          - vlan_id: 100
            name: WORKSHOP_VLAN
        state: merged

    - name: Verify VLANs
      cisco.ios.ios_command:
        commands:
          - show vlan brief
      register: vlan_output

    - name: Display VLAN table
      ansible.builtin.debug:
        var: vlan_output.stdout_lines
```

### 3.4 Saving the Configuration

> *(Instructor: Don't skip this — a common gotcha for those new to IOS automation)*

- Difference between running-config and startup-config
- Using `cisco.ios.ios_config` with `save_when: always` or a dedicated save task

```yaml
    - name: Save configuration
      cisco.ios.ios_config:
        save_when: always
```

---

## Section Wrap-Up

> *(Instructor: Quick recap before moving into the CI/CD section)*

**Key takeaways from Part 1:**

- Ansible is agentless and communicates over SSH — no agents needed on network devices
- Inventory files define *what* you're managing; playbooks define *what to do*
- Variables keep credentials and environment-specific data out of your playbooks
- Always verify changes — use `--check`, gather facts before/after, and confirm with `show` commands
- Idempotency means you can run playbooks repeatedly without fear of creating duplicate config

**Coming up next:** Intro to CI/CD pipelines — how to take these playbooks and put guardrails around them with GitLab, linting, and automated validation.

---

*End of Part 1*


# Part 2: CI/CD for Network Automation

> **Instructor Note:** This section assumes a self-hosted GitLab instance is already running and accessible from the students' WSL environments. A GitLab Runner should be pre-registered and confirmed healthy before the workshop. Students should have a GitLab account and access to the workshop project repository.

---

## Section 4: Introduction to CI/CD

### 4.1 Why CI/CD for Network Automation?

> *(Instructor: Use the "why does this matter" moment here — tell a short story about a config change that broke production and how a pipeline would have caught it before it hit a real device.)*

Topics to cover:
- What CI/CD means in a traditional software context
- Why the same principles apply to network automation
- The risk of running untested playbooks directly against production devices
- The pipeline as a safety net, not a bureaucratic hurdle

Key concepts:
- **Pipeline** — an automated sequence of jobs triggered by a code event (e.g. a git push)
- **Stage** — a logical grouping of jobs (e.g. validate, test, deploy)
- **Job** — a single unit of work inside a stage
- **GitLab Runner** — the agent that executes pipeline jobs

### 4.2 Our Pipeline — The Big Picture

> *(Instructor: Walk through the end-to-end flow before diving into any individual piece. A whiteboard sketch or diagram here works well.)*

The pipeline we'll build follows this flow:

```
Developer pushes playbook changes to GitLab
        │
        ▼
┌───────────────┐
│   Pre-Check   │  pyATS snapshots the network state before changes
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Deploy     │  Ansible pushes the changes to devices
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Post-Check   │  pyATS validates state after changes, diffs against pre
└───────────────┘
```

- Changes are only deployed if pre-check passes
- Post-check automatically flags unexpected state changes
- The pipeline result is visible in GitLab — pass or fail

---

## Section 5: GitLab Project Setup

### 5.1 Repository Structure

> *(Instructor: Show the project repository that has been pre-created for the workshop. Walk through how it maps to what they built in Part 1.)*

```
network-automation/
├── .gitlab-ci.yml          ← pipeline definition lives here
├── ansible.cfg
├── inventory/
│   └── hosts.yml
├── group_vars/
│   └── all.yml
├── playbooks/
│   ├── push_changes.yml
│   └── rollback.yml
└── tests/
    ├── pre_check.py
    └── post_check.py
```

### 5.2 Introduction to `.gitlab-ci.yml`

> *(Instructor: This file is the heart of the pipeline — spend time here. Students don't need to write it from scratch but should understand every section.)*

Topics to cover:
- How GitLab reads `.gitlab-ci.yml` on every push
- `stages` — defining the order of execution
- `image` — the Docker image (or executor environment) each job runs in
- `before_script` — setup steps that run before every job
- `only` / `rules` — controlling when jobs trigger

**Workshop `.gitlab-ci.yml` skeleton to walk through:**

```yaml
stages:
  - pre_check
  - deploy
  - post_check

variables:
  ANSIBLE_HOST_KEY_CHECKING: "False"

before_script:
  - pip install pyats genie ansible cisco.ios --quiet

pre_check:
  stage: pre_check
  script:
    - python tests/pre_check.py
  artifacts:
    paths:
      - pre_snapshot.json

deploy:
  stage: deploy
  script:
    - ansible-playbook playbooks/push_changes.yml
  needs:
    - pre_check

post_check:
  stage: post_check
  script:
    - python tests/post_check.py
  needs:
    - deploy
```

### 5.3 GitLab Runner — How Jobs Actually Run

> *(Instructor: Brief explanation — students often wonder "where does this actually execute?")*

- The self-hosted Runner picks up jobs from GitLab
- The Runner environment needs reachability to both GitLab and the CML devices
- Show the Runner status in GitLab: **Settings → CI/CD → Runners**

---

## Section 6: Pre- and Post-Validation with pyATS

### 6.1 What is pyATS?

> *(Instructor: Quick intro — don't go deep on the framework internals, just enough context for the demo to make sense.)*

- Cisco's Python-based test and validation framework
- **pyATS** = the test framework; **Genie** = the library of parsers and APIs on top of it
- Can connect to devices, run `show` commands, and return structured (parsed) data
- Used heavily in Cisco's own internal testing — built for network engineers

Key concepts for this section:
- **Testbed** — pyATS equivalent of an Ansible inventory (defines devices and credentials)
- **Snapshot** — capturing the current state of the network as structured data
- **Diff** — comparing two snapshots to identify what changed

### 6.2 The pyATS Testbed File

> *(Instructor: Show how the testbed maps to the Ansible inventory students already built — same devices, different format.)*

```yaml
# tests/testbed.yml
testbed:
  name: workshop_lab

devices:
  sw1:
    os: ios
    type: switch
    credentials:
      default:
        username: admin
        password: "{{ lab_password }}"
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.x.x
```

### 6.3 Pre-Check Script Walkthrough

> *(Instructor: Walk through the pre-built script — students do NOT write this from scratch. Focus on what it does, not how every line works.)*

What the pre-check script does:
- Connects to all devices using the testbed
- Runs a set of `show` commands and parses the output via Genie
- Saves the structured result as `pre_snapshot.json`
- Exits cleanly if all devices respond; fails the pipeline stage if any device is unreachable

**`tests/pre_check.py` — key sections to highlight:**

```python
from genie.testbed import load
import json

# Load the testbed
testbed = load("tests/testbed.yml")

snapshot = {}

for device_name, device in testbed.devices.items():
    device.connect(log_stdout=False)

    # Capture structured state
    snapshot[device_name] = {
        "interfaces": device.parse("show interfaces"),
        "vlans": device.parse("show vlan brief"),
        "bgp": device.parse("show ip bgp summary"),  # remove if not applicable
    }

    device.disconnect()

# Save snapshot to file (passed as artifact to post-check)
with open("pre_snapshot.json", "w") as f:
    json.dump(snapshot, f, indent=2)

print("Pre-check complete. Snapshot saved.")
```

### 6.4 Post-Check Script Walkthrough

> *(Instructor: Show how the post-check loads the pre-snapshot artifact and compares it to current state. The diff output is the payoff moment — show a real diff if possible.)*

What the post-check script does:
- Loads `pre_snapshot.json` from the pipeline artifact
- Reconnects to all devices and captures state again
- Diffs the two snapshots
- Prints a summary of what changed and exits non-zero if unexpected changes are detected

**`tests/post_check.py` — key sections to highlight:**

```python
from genie.testbed import load
from genie.utils.diff import Diff
import json

testbed = load("tests/testbed.yml")

with open("pre_snapshot.json") as f:
    pre_snapshot = json.load(f)

issues_found = False

for device_name, device in testbed.devices.items():
    device.connect(log_stdout=False)

    post_state = {
        "interfaces": device.parse("show interfaces"),
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
```

### 6.5 Lab Task — Trigger the Pipeline

> *(Instructor: Have students make a small change to a playbook and push it to GitLab. Watch the pipeline run together.)*

Steps:
1. Make a minor change to `playbooks/push_changes.yml` (e.g. add a new interface description)
2. Commit and push to the `main` branch
3. Navigate to **CI/CD → Pipelines** in GitLab and watch the stages execute
4. Review the job logs for each stage — pre-check, deploy, post-check
5. Examine the diff output in the post-check job log

**Discussion points after the pipeline runs:**
- What would cause the post-check to fail?
- What happens if the deploy job fails — does post-check still run?
- How would you add a rollback job triggered on failure?

---

## Section 7: The Digital Twin — Testing Before You Touch Production

### 7.1 The Problem We're Solving

> *(Instructor: This is the "so what" moment for the whole workshop. Connect it back to the story from Section 4.1.)*

- Even with a CI/CD pipeline, your playbooks are still running against real devices in the deploy stage
- What if you could validate the playbook logic itself — before it ever touches production?
- Enter: the CML "mini network" as a digital twin

### 7.2 How the Mini Network Works

> *(Instructor: Show the CML topology. Keep this conceptual — students don't need to build it, just understand the idea.)*

Topics to cover:
- A lightweight CML topology that mirrors the key elements of the production network
- Same device types, same IOS versions, representative config
- Separate inventory file pointing at the CML devices instead of production

```
network-automation/
├── inventory/
│   ├── hosts.yml          ← production inventory
│   └── hosts_cml.yml      ← CML twin inventory (same structure, different IPs)
```

### 7.3 Extending the Pipeline for Twin Testing

> *(Instructor: Show how a single variable or inventory swap can redirect the pipeline at the CML lab instead of production.)*

- Add a `test_in_twin` stage before `deploy` that runs the playbook against `hosts_cml.yml`
- If the twin stage fails, the pipeline stops before anything touches production
- On merge requests, run twin only; on merge to main, run full pipeline

**Extended pipeline concept:**

```yaml
stages:
  - pre_check
  - test_in_twin     ← new stage
  - deploy
  - post_check

test_in_twin:
  stage: test_in_twin
  script:
    - ansible-playbook playbooks/push_changes.yml -i inventory/hosts_cml.yml
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### 7.4 Demo — Catching a Bad Playbook in the Twin

> *(Instructor: Pre-stage a playbook with a deliberate error — wrong VLAN ID, bad interface name, etc. Run it through the pipeline and show it failing safely in CML before it could have hit production.)*

Walk through:
1. Show the "bad" playbook change in GitLab
2. Open a merge request — pipeline triggers twin test only
3. Watch the twin stage fail with a clear error
4. Show that `deploy` never ran — production is untouched
5. Fix the playbook, push again, watch the twin pass, merge to main, full pipeline runs

---

## Section Wrap-Up

> *(Instructor: Bring it all together — connect every piece of the workshop into one narrative.)*

**Key takeaways from Part 2:**

- A CI/CD pipeline turns manual, error-prone playbook runs into a repeatable, auditable process
- pyATS pre- and post-checks give you eyes on the network state before and after every change
- The digital twin in CML adds a safety layer — bad playbooks fail in a lab, not in production
- GitLab artifacts carry state between pipeline stages (pre-snapshot → post-check)
- This entire workflow runs automatically on every push — no human has to remember to test

**The full workflow in one sentence:** *Push a change → test it in the twin → snapshot production state → deploy → verify nothing unexpected changed.*

---

*End of Workshop Lab Guide*