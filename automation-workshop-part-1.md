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
