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

Discussion questions:
- What problem does Ansible solve?
- Why is it important for Network Engineers?

Topics to cover:
- Agentless automation — how it works over SSH/NETCONF
- Idempotency — what it means and why it matters in networking
- Key terms to know: **Control node**, **Managed nodes**, **Playbook**, **Task**, **Module**

### 1.2 Ansible Project Structure

As Ansible runs only on Linux, we will be working solely in WSL within the Windows jumphost.
The following is an overview of the directory structure of our Ansible project. Note that the actual repository include additional files not shown we'll speak to later!

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
└── vars
    └── vlans.yml
```

Key components to walk through:

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
# ~/ansible-cml/inventory/prod/hosts.yaml

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
        switches:
          children:
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
Topics to cover:
- Where to define credentials (vars vs group_vars vs vault)
- Common network variables: `ansible_network_os`, `ansible_connection`, `ansible_become`
- Brief mention of **Ansible Vault** for credential security

**Example group_vars file :**

```yaml
# ~/ansible-cml/inventory/prod/group_vars/all.yml`
ansible_user: admin
ansible_password: "{{ vault_password }}"
ansible_network_os: cisco.ios.ios
ansible_connection: network_cli
ansible_become: yes
ansible_become_method: enable
```

### 1.5 `ansible.cfg` Walkthrough
The `ansible.cfg` file represents default configuration values for the Ansible engine itself.
This could include how Ansible connects to devices, SSH settings, and default paths to use. 

```ini
[defaults]
inventory = ./inventory/digital-twin/hosts.yaml
remote_user = ansible
host_key_checking = False
```

---

## Section 2: Getting Started with Ansible

### 2.1 Your First Command — `ansible` Ad-Hoc

Discussion questions:
- Why did we use ios_ping and not Ansible ping?

While the goal is to utilize Ansible in a structured pipeline, it can also be used as needed for ad-hoc checks.

- Syntax: `ansible <host/group> -m <module> -i <inventory-path> -a <args> `
- Run a connection test/ping against all devices to confirm connectivity

**Lab Task 2.1 — Ad-Hoc Ping:**

```bash
ansible all -m cisco.ios.ios_ping -a "dest=198.18.128.1 vrf=Mgmt-vrf"
```

### 2.2 Anatomy of a Playbook
Now, walking through a basic playbook, let's take a look at what each part means and how its used.

- `hosts:` — which inventory targets to run against
- `gather_facts:` — typically disabled for network devices
- `tasks:` — ordered list of modules to execute
- `name:` — human-readable label for each task

Below is an example skeleton for us to work through:

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

You already have a network... How can we get started with using Ansible in a brownfield environment? Visibility!

Topics to cover:
- Using `cisco.ios.ios_command` to run `show` commands
- Capturing output with `register`
- Displaying output with `debug`

**Lab Task 2.2 — Gather Device Info:**

```yaml
---
- name: Basic Discovery
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

It is important to note the difference between raw data captured and structured data!

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

Discussion Points:
 - Idempotency by design and philosophy
 - Idempotency in practice

```
# Idempotent — checks state before acting
cisco.ios.ios_vlans:
  config:
    - vlan_id: 10
      name: MANAGEMENT

# NOT idempotent — always pushes the command regardless
cisco.ios.ios_command:
  commands:
    - vlan 10
```

### 3.1 Making Changes Safely — `check` Mode

Discussion Points:
- What `--check` does and when to use it
- Its limitations on network devices (not all modules support it fully)

```bash
ansible-playbook playbooks/enforce_vlans.yml --check
```

### 3.2 Lab Task — Updating Interface Descriptions

Let's start with a low risk change. We will modify the interface descriptions for access switch uplinks.

- Using `cisco.ios.ios_interfaces` to set interface descriptions
- Verifying the change with a follow-up `show` task

```yaml
# Snippet of ~/ansible-cml/playbooks/enforce_motd.yml

- name: Enforce MOTD Banner on Cisco IOS Devices
  hosts: all
  gather_facts: false
  connection: network_cli

  vars_files:
    - ../group_vars/all/vlans.yml

  tasks:
    - name: Apply MOTD banner
      cisco.ios.ios_banner:
        banner: motd
        text: "{{ motd }}"
        state: present
```

### 3.3 Lab Task — Enforcing VLANs

In this task, we'll go for a more disruptive change, enforcing specific VLANs.

- Using `cisco.ios.ios_vlans` to configure VLANs
- Explaining `state: replaced` vs `state: overriden` vs `state: deleted`

```yaml
---
- name: Enforce VLAN Source of Truth
  hosts: switches
  gather_facts: no

  tasks:
    - name: Enforce VLANs from source of truth
      cisco.ios.ios_vlans:
        config: "{{ vlans }}"
        state: replaced

    - name: Confirm applied VLANs
      cisco.ios.ios_facts:
        gather_subset: all
        gather_network_resources:
          - vlans

    - name: Display configured VLANs
      ansible.builtin.debug:
        msg: "{{ ansible_network_resources.vlans }}"
```

### 3.4 Saving the Configuration

- Remember running-config vs. startup-config!
- Using `cisco.ios.ios_config` with `save_when:` or a dedicated save task

```yaml
    - name: Save configuration
      cisco.ios.ios_config:
        save_when: modified
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
 
The lab already has the repo loaded locally and the GitHub runner installd.
Before we begin, let's make sure we sync your GitHub accounts with the environment and get the GitHub Actions runner registered locally.
To do so, we will create an SSH key for registering to GitHub, and then pull a registration token from GitHub for the runner.

```bash
ssh-keygen -t ed25519 -C "name@email.com"   # new SSH key
./config.sh --url <repo> --token <token>      # register runner
```
 
---
 
## Section 4: Introduction to CI/CD
 
### 4.1 Why CI/CD for Network Automation?
 
Discussion points:
- What CI/CD means in a traditional software context
- Any examples of config changes that broke production?
- Why the same principles apply to network automation
- The risk of running untested playbooks directly against production devices
- The pipeline as a safety net, not a bureaucratic hurdle
 
Key concepts:
- **Workflow** — an automated sequence of jobs triggered by a code event (e.g. a git push)
- **Job** — a logical grouping of steps (e.g. validate, test, deploy)
- **Step** — a single unit of work inside a job
- **GitHub Actions Runner** — the local agent that executes workflow jobs
 
### 4.2 Our Pipeline — The Big Picture
  
The pipeline we'll build follows the flow below.
One thing to note is that our workflow applies to different inventories depending on the type of action that was taken.
We'll touch on that later on in the workshop.
 
```
Developer pushes playbook changes to GitHub
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
- The workflow result is visible in GitHub — pass or fail, shown on the Actions tab and on pull requests
 
---
 
## Section 5: GitHub Project Setup
 
### 5.1 Repository Structure
  
To our repository we add a directory for our workflows and one for our PyATS validations.
This is a toy example for education purposes but in a production environment you're likely to have more workflows and tests depending on your needs.

```
network-automation/
├── .github/
│   └── workflows/
│       └── network-automation.yaml
├── ansible.cfg
├── inventory/
├── playbooks/
├── vars/
└── tests/
    ├── pre_check.py
    └── post_check.py
```
 
### 5.2 Introduction to `network-automation.yml`
  
Topics to cover:
- How GitHub reads workflow files from `.github/workflows/` on every push
- `on` — the trigger events (push, pull_request, workflow_dispatch)
- `jobs` — defining the jobs and their order of execution
- `runs-on` — the runner environment each job uses
- `steps` — the ordered list of commands and actions within a job
- `if` / conditions — controlling when jobs trigger
 
**Workshop `network-automation.yaml` skeleton to walk through:**
 
```yaml
name: Network Automation Pipeline
 
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
 
env:
  ANSIBLE_HOST_KEY_CHECKING: "False"
 
jobs:
  pre_check:
    runs-on: self-hosted
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
 
      - name: Install dependencies
        run: pip install pyats genie ansible cisco.ios --quiet
 
      - name: Run pre-check snapshot
        run: python tests/pre_check.py
 
      - name: Upload pre-snapshot artifact
        uses: actions/upload-artifact@v4
        with:
          name: pre-snapshot
          path: pre_snapshot.json
 
  deploy:
    runs-on: self-hosted
    needs: pre_check
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
 
      - name: Install dependencies
        run: pip install ansible cisco.ios --quiet
 
      - name: Deploy changes
        run: ansible-playbook playbooks/push_changes.yml
 
  post_check:
    runs-on: self-hosted
    needs: deploy
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
 
      - name: Install dependencies
        run: pip install pyats genie --quiet
 
      - name: Download pre-snapshot artifact
        uses: actions/download-artifact@v4
        with:
          name: pre-snapshot
 
      - name: Run post-check validation
        run: python tests/post_check.py
```
 
### 5.3 GitHub Actions Runner
 
How do the jobs actually run? 
- The self-hosted Runner picks up jobs from GitHub Actions
- The Runner environment needs reachability to both GitHub and the CML devices
- Show the Runner status in GitHub: **Settings → Actions → Runners**
 
---
 
## Section 6: Pre- and Post-Validation with pyATS
 
### 6.1 What is pyATS?

Discussion points: 
- Cisco's Python-based test and validation framework
- **pyATS** = the test framework; **Genie** = the library of parsers and APIs on top of it
- Can connect to devices, run `show` commands, and return structured (parsed) data
- Used heavily in Cisco's own internal testing — built for network engineers
 
Key concepts for this section:
- **Testbed** — pyATS equivalent of an Ansible inventory (defines devices and credentials)
- **Snapshot** — capturing the current state of the network as structured data
- **Diff** — comparing two snapshots to identify what changed
 
### 6.2 The pyATS Testbed File

The testbed maps closely to the inventory files we created for Ansible! Just with different syntax... 
 
```yaml
# tests/testbed/lab_testbed.yaml
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
testbed = load("tests/testbed/lab_testbed.yml")
 
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
 
testbed = load("tests/testbed/testbed.yml")
 
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
 
### 6.5 Lab Task — Trigger the Workflow
  
Steps:
1. Create a new feature branch with Git. (`git checkout -b feature/update-motd`)
2. Make a minor change to `playbooks/update_motd.yml` (e.g. add different language)
3. Commit and push to the `feature/update-motd` branch (`git add .` -> `git commit -m "message"` -> `git push origin feature/update-motd`)
4. Navigate to GitHub and open a PR request for the recent feature branch push.
5. Navigate to the **Actions** tab in GitHub and watch the jobs execute
6. Review the step logs for each job — pre-check, deploy, post-check
7. Examine the diff output in the post-check job log
 
**Discussion points after the pipeline runs:**
- What would cause the post-check to fail?
- What happens if the deploy job fails — does post-check still run?
- How would you add a rollback job triggered on failure?
- What if we decide to merge the changes?
 
---
 
## Section 7: The Digital Twin — Testing Before You Touch Production
 
### 7.1 The Problem We're Solving
  
- Even with a CI/CD pipeline, your playbooks are still running against real devices in the deploy stage
- What if you could validate the playbook logic itself — before it ever touches production?
- Enter: the CML "mini network" as a digital twin
 
### 7.2 How the Mini Network Works
  
Topics to cover:
- A lightweight CML topology that mirrors the key elements of the production network
- Same device types, same IOS versions, representative config
- Separate inventory file pointing at the CML devices instead of production
 
```
network-automation/
├── .github/
│   └── workflows/
│       └── network-automation.yml
├── inventory/
│   ├── hosts.yml          ← production inventory
│   └── hosts_cml.yml      ← CML twin inventory (same structure, different IPs)
```
 
### 7.3 Extending the Pipeline for Twin Testing
  
- Add a `test_in_twin` job before `deploy` that runs the playbook against `hosts_cml.yml`
- If the twin job fails, the workflow stops before anything touches production
- On pull requests, run twin only; on merge to main, run the full workflow
 
**Extended workflow concept:**
 
```yaml
name: Network Automation Pipeline
 
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
 
jobs:
  pre_check:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: python tests/pre_check.py
      - uses: actions/upload-artifact@v4
        with:
          name: pre-snapshot
          path: pre_snapshot.json
 
  test_in_twin:        # ← new job
    runs-on: self-hosted
    needs: pre_check
    steps:
      - uses: actions/checkout@v4
      - run: ansible-playbook playbooks/push_changes.yml -i inventory/hosts_cml.yml
 
  deploy:
    runs-on: self-hosted
    needs: test_in_twin
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: ansible-playbook playbooks/push_changes.yml
 
  post_check:
    runs-on: self-hosted
    needs: deploy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: pre-snapshot
      - run: python tests/post_check.py
```
 
### 7.4 Demo — Catching a Bad Playbook in the Twin
 
> *(Instructor: Pre-stage a playbook with a deliberate error — wrong VLAN ID, bad interface name, etc. Run it through the pipeline and show it failing safely in CML before it could have hit production.)*
 
Walk through:
1. Show the "bad" playbook change in GitHub
2. Open a pull request — workflow triggers twin test only
3. Watch the twin job fail with a clear error
4. Show that `deploy` never ran — production is untouched
5. Fix the playbook, push again, watch the twin pass, merge to main, full workflow runs
 
---
 
## Section Wrap-Up
  
**Key takeaways from Part 2:**
 
- A CI/CD workflow turns manual, error-prone playbook runs into a repeatable, auditable process
- pyATS pre- and post-checks give you eyes on the network state before and after every change
- The digital twin in CML adds a safety layer — bad playbooks fail in a lab, not in production
- GitHub Actions artifacts carry state between jobs (pre-snapshot → post-check)
- This entire workflow runs automatically on every push — no human has to remember to test
 
**The full workflow in one sentence:** *Push a change → test it in the twin → snapshot production state → deploy → verify nothing unexpected changed.*
 
---
 
*End of Workshop Lab Guide*