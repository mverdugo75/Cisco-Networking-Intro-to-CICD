"""
Shared helpers for pre/post pipeline checks focused on platform stability:
CPU headroom, memory growth vs baseline, ICMP reachability, optional RIB checks.

Uses **Genie** ``device.parse()`` for IOS/XE structured parsing (the same model as the
workshop). Falls back to ``execute()`` plus small regex helpers only when no parser
matches or the output is empty / non-standard.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import yaml
from genie.libs.parser.utils.common import ParserNotFound
from genie.metaparser.util.exceptions import SchemaEmptyParserError
from genie.testbed import load


def repo_base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_testbed() -> Any:
    base = repo_base_dir()
    testbed_env = os.environ.get("TESTBED_ENV", "lab")
    testbed_map = {
        "lab": "tests/testbed/lab_testbed.yaml",
        "prod": "tests/testbed/prod_testbed.yaml",
    }
    path = testbed_map.get(testbed_env)
    if path is None:
        raise ValueError(
            f"Unknown TESTBED_ENV: '{testbed_env}'. Must be 'lab' or 'prod'."
        )
    return load(os.path.join(base, path))


def load_checks_config() -> dict[str, Any]:
    path = os.path.join(repo_base_dir(), "tests", "stability_checks.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def threshold_defaults(cfg: dict[str, Any]) -> dict[str, float]:
    t = cfg.get("thresholds") or {}
    return {
        "cpu_five_seconds_max_pct": float(t.get("cpu_five_seconds_max_pct", 90)),
        "cpu_five_seconds_increase_max_pct": float(
            t.get("cpu_five_seconds_increase_max_pct", 35)
        ),
        "memory_used_pct_increase_max": float(
            t.get("memory_used_pct_increase_max", 15)
        ),
    }


def _genie_parse(device: Any, cmd: str, **kwargs: Any) -> Optional[dict[str, Any]]:
    """Run Genie parser; return None if no parser or output does not match schema."""
    try:
        parsed = device.parse(cmd, **kwargs) if kwargs else device.parse(cmd)
    except (SchemaEmptyParserError, ParserNotFound):
        return None
    if not parsed:
        return None
    return parsed


def cpu_util_from_genie(parsed: dict[str, Any]) -> dict[str, Optional[int]]:
    """Normalize Genie ``show processes cpu`` / ``show processes cpu sorted`` output."""
    if "five_sec_cpu_total" in parsed:
        return {
            "five_sec": parsed.get("five_sec_cpu_total"),
            "one_min": parsed.get("one_min_cpu"),
            "five_min": parsed.get("five_min_cpu"),
        }
    core = parsed.get("core") or {}
    best_five: Optional[int] = None
    best_one: Optional[int] = None
    best_five_min: Optional[int] = None
    for _name, cdata in core.items():
        if not isinstance(cdata, dict):
            continue
        v = cdata.get("five_sec_cpu_total")
        if v is not None and (best_five is None or v > best_five):
            best_five = int(v)
            best_one = cdata.get("one_min_cpu")
            best_five_min = cdata.get("five_min_cpu")
    if best_five is not None:
        return {
            "five_sec": best_five,
            "one_min": int(best_one) if best_one is not None else None,
            "five_min": int(best_five_min) if best_five_min is not None else None,
        }
    return {"five_sec": None, "one_min": None, "five_min": None}


def parse_cpu_utilization(output: str) -> dict[str, Optional[int]]:
    """Fallback: headline CPU line from raw ``show processes cpu`` output."""
    five = one = five_min = None
    m = re.search(
        r"CPU utilization for five seconds:\s*(\d+)%", output, re.IGNORECASE
    )
    if m:
        five = int(m.group(1))
    m = re.search(r"one minute:\s*(\d+)%", output, re.IGNORECASE)
    if m:
        one = int(m.group(1))
    m = re.search(r"five minutes:\s*(\d+)%", output, re.IGNORECASE)
    if m:
        five_min = int(m.group(1))
    return {"five_sec": five, "one_min": one, "five_min": five_min}


def cpu_sample_from_device(device: Any) -> dict[str, Any]:
    parsed = _genie_parse(device, "show processes cpu")
    if parsed:
        cpu = cpu_util_from_genie(parsed)
        if cpu.get("five_sec") is not None:
            return cpu
    try:
        out = device.execute("show processes cpu")
    except Exception as exc:
        return {"error": str(exc)}
    return parse_cpu_utilization(out)


def memory_used_pct_from_genie(parsed: dict[str, Any]) -> Optional[float]:
    names = parsed.get("name") or {}
    proc = names.get("processor")
    if not isinstance(proc, dict):
        return None
    total = proc.get("total")
    used = proc.get("used")
    if isinstance(total, int) and isinstance(used, int) and total > 0:
        return (used / total) * 100.0
    return None


def parse_processor_memory_used_pct(output: str) -> Optional[float]:
    m = re.search(r"Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)", output)
    if m:
        total, used, _free = map(int, m.groups())
        if total > 0:
            return (used / total) * 100.0
    return None


def memory_used_percent(device: Any) -> Optional[float]:
    parsed = _genie_parse(device, "show memory statistics")
    if parsed:
        pct = memory_used_pct_from_genie(parsed)
        if pct is not None:
            return pct
    for cmd in ("show memory statistics", "show memory"):
        try:
            out = device.execute(cmd)
        except Exception:
            continue
        pct = parse_processor_memory_used_pct(out)
        if pct is not None:
            return pct
    return None


def parse_ping_success_rate(output: str) -> Optional[int]:
    m = re.search(r"Success rate is (\d+) percent", output, re.IGNORECASE)
    return int(m.group(1)) if m else None


def ping_success_from_genie(parsed: dict[str, Any]) -> Optional[int]:
    try:
        rate = parsed["ping"]["statistics"]["success_rate_percent"]
        return int(rate)
    except (KeyError, TypeError, ValueError):
        return None


def ping_target(device: Any, addr: str, management_vrf: str) -> Optional[int]:
    """ICMP via management VRF (matches Genie ``ping vrf …`` + IOS fallback)."""
    parsed = _genie_parse(
        device,
        "ping",
        vrf=management_vrf,
        addr=addr,
        count=3,
        timeout=1,
    )
    if parsed:
        rate = ping_success_from_genie(parsed)
        if rate is not None:
            return rate
    try:
        out = device.execute(
            f"ping vrf {management_vrf} {addr} repeat 3 timeout 1"
        )
    except Exception:
        return None
    return parse_ping_success_rate(out)


def route_present_from_genie(parsed: dict[str, Any]) -> bool:
    if parsed.get("entry"):
        return True
    if parsed.get("default_gateway"):
        return True
    return False


def route_present_from_raw(output: str) -> bool:
    if re.search(r"Subnet not in table|not in routing table", output, re.IGNORECASE):
        return False
    if re.search(r"% Invalid", output):
        return False
    return bool(
        re.search(
            r"(Routing entry|Known via|directly connected|via\s+\d+\.\d+\.\d+\.\d+)",
            output,
            re.IGNORECASE,
        )
    )


def route_prefix_present(device: Any, prefix: str, management_vrf: str) -> bool:
    """RIB lookup in management VRF (Genie ``show ip route`` distributor + IOS fallback)."""
    parsed = _genie_parse(
        device,
        "show ip route",
        vrf=management_vrf,
        route=prefix,
    )
    if parsed is not None:
        return route_present_from_genie(parsed)
    try:
        out = device.execute(f"show ip route vrf {management_vrf} {prefix}")
    except Exception:
        return False
    return route_present_from_raw(out)


def collect_device_sample(device: Any, cfg: dict[str, Any]) -> dict[str, Any]:
    """Single-device stability sample (baseline or post-run)."""
    sample: dict[str, Any] = {
        "cpu": cpu_sample_from_device(device),
        "memory_used_pct": memory_used_percent(device),
        "ping": {},
        "routes_ok": {},
    }

    mgmt_vrf = str(cfg.get("management_vrf") or "Mgmt-vrf")

    for addr in cfg.get("ping_targets") or []:
        sample["ping"][addr] = ping_target(device, addr, mgmt_vrf)

    for prefix in cfg.get("required_route_prefixes") or []:
        sample["routes_ok"][prefix] = route_prefix_present(device, prefix, mgmt_vrf)

    return sample


def precheck_device_ok(sample: dict[str, Any]) -> tuple[bool, list[str]]:
    """Fail fast if we cannot reach ping targets or mandatory routes before deploy."""
    issues: list[str] = []
    for addr, rate in sample.get("ping", {}).items():
        if rate is None:
            issues.append(f"ping {addr}: no parseable result (unreachable or CLI error)")
        elif rate < 100:
            issues.append(f"ping {addr}: success rate {rate}% (expected 100%)")

    for prefix, ok in sample.get("routes_ok", {}).items():
        if not ok:
            issues.append(f"route {prefix}: not present in RIB")

    return (len(issues) == 0, issues)


def compare_samples(
    pre: dict[str, Any],
    post: dict[str, Any],
    thresholds: dict[str, float],
) -> list[str]:
    """Return human-readable issues when post-run stability regresses."""
    issues: list[str] = []

    pre_cpu = pre.get("cpu") or {}
    post_cpu = post.get("cpu") or {}
    pre_five = pre_cpu.get("five_sec")
    post_five = post_cpu.get("five_sec")

    if post_five is None:
        issues.append("CPU: could not parse five-second utilization post-change")
    else:
        if post_five > thresholds["cpu_five_seconds_max_pct"]:
            issues.append(
                f"CPU: five-second {post_five}% exceeds ceiling "
                f"{thresholds['cpu_five_seconds_max_pct']:.0f}%"
            )
        if (
            pre_five is not None
            and post_five - pre_five > thresholds["cpu_five_seconds_increase_max_pct"]
        ):
            issues.append(
                f"CPU: five-second jumped from {pre_five}% to {post_five}% "
                f"(max allowed increase "
                f"{thresholds['cpu_five_seconds_increase_max_pct']:.0f} points)"
            )

    pre_mem = pre.get("memory_used_pct")
    post_mem = post.get("memory_used_pct")
    if pre_mem is not None and post_mem is not None:
        delta = post_mem - pre_mem
        if delta > thresholds["memory_used_pct_increase_max"]:
            issues.append(
                f"Memory: processor used {pre_mem:.1f}% -> {post_mem:.1f}% "
                f"(+{delta:.1f} points; max allowed +"
                f"{thresholds['memory_used_pct_increase_max']:.0f} points)"
            )
    elif post_mem is None:
        issues.append("Memory: could not parse processor utilization post-change")

    for addr, rate in (post.get("ping") or {}).items():
        if rate is None:
            issues.append(f"ping {addr}: no parseable result post-change")
        elif rate < 100:
            issues.append(f"ping {addr}: success rate {rate}% post-change (expected 100%)")

    for prefix, ok in (post.get("routes_ok") or {}).items():
        if not ok:
            issues.append(f"route {prefix}: missing from RIB post-change")

    return issues
