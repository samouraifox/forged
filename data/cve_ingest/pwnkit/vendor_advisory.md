# CVE-2021-4034 — PwnKit pkexec LPE — Red Hat Vendor Advisory RHSB-2022-001

**Source URL:** https://access.redhat.com/security/vulnerabilities/RHSB-2022-001
**CVE:** CVE-2021-4034
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

## Vulnerability Overview

Red Hat documented a critical privilege escalation flaw in pkexec. The advisory states: "an unprivileged local attacker to escalate privileges, bypassing any authentication" through improper argument vector handling.

## Affected Products

- Red Hat Enterprise Linux 6, 7, 8
- Red Hat Virtualization 4
- Container images based on RHEL shipping polkit
- Layered products (OpenShift, OpenStack, etc.)

## Severity and Timeline

**Rating:** Important
**CVE:** CVE-2021-4034
**Published:** January 12, 2022
**Updated:** February 15, 2022

## Technical Root Cause

The vulnerability stems from pkexec failing to validate argument counts. When the argument array is empty, pkexec interprets environment variables as executable commands, allowing attackers to execute arbitrary code with elevated privileges.

## Remediation Options

**Permanent Fix:**
Apply polkit package updates via provided errata (RHSA-2022:0267 through RHSA-2022:0540 for various RHEL versions).

**Temporary Mitigation:**
SystemTap-based kernel module blocking pkexec execution without arguments—requires debuginfo installation and systemtap packages. Note: "This mitigation doesn't work for Secure Boot enabled systems."

## Notable FAQ Points

- No service restart required after patching
- Removing the setuid bit is explicitly **not recommended** as it breaks legitimate functionality
- Docker networking may require configuration persistence after updates
