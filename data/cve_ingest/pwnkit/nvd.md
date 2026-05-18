# CVE-2021-4034 — Polkit pkexec Local Privilege Escalation (PwnKit) — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2021-4034
**CVE:** CVE-2021-4034
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Title
CVE-2021-4034 Detail - National Vulnerability Database

## Description
"A local privilege escalation vulnerability was found on polkit's pkexec utility. The pkexec application is a setuid tool designed to allow unprivileged users to run commands as privileged users according predefined policies. The current version of pkexec doesn't handle the calling parameters count correctly and ends trying to execute environment variables as commands."

The vulnerability allows attackers to craft malicious environment variables to execute arbitrary code, resulting in local privilege escalation.

## CVSS Scores

**CVSS v3.1 (NIST/CISA-ADP):**
- Base Score: 7.8 HIGH
- Vector: CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H

**CVSS v2.0 (NIST):**
- Base Score: 7.2 HIGH
- Vector: (AV:L/AC:L/Au:N/C:C/I:C/A:C)

## Weakness Types (CWE)
- CWE-125: Out-of-bounds Read
- CWE-787: Out-of-bounds Write

## Key Dates
- NVD Published: 01/28/2022
- Last Modified: 11/06/2025

## Key References

| URL | Type |
|-----|------|
| https://access.redhat.com/security/vulnerabilities/RHSB-2022-001 | Mitigation, Vendor Advisory |
| https://bugzilla.redhat.com/show_bug.cgi?id=2025869 | Issue Tracking, Patch |
| https://gitlab.freedesktop.org/polkit/polkit/-/commit/a2bf5c9c83b6ae46cbd5c779d3055bff81ded683 | Patch |
| https://www.qualys.com/2022/01/25/cve-2021-4034/pwnkit.txt | Exploit, Mitigation |
| https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2021-4034 | US Government Resource |

## Additional Notable References
- Red Hat security advisories and bug tracking
- Siemens product security notices
- Oracle CPU alerts
- SUSE support documentation

## CISA KEV Status
This vulnerability is tracked in CISA's Known Exploited Vulnerabilities Catalog with a due date of 07/18/2022 for applying vendor updates.
