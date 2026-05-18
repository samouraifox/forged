# NVD entry for CVE-2022-0847

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2022-0847
**CVE:** CVE-2022-0847
**Fetched:** 2026-05-18
**Source type:** nvd

---

## CVE ID

CVE-2022-0847

## Description

"A flaw was found in the way the 'flags' member of the new pipe buffer structure was lacking proper initialization in copy_page_to_iter_pipe and push_pipe functions in the Linux kernel and could thus contain stale values. An unprivileged local user could use this flaw to write to pages in the page cache backed by read only files and as such escalate their privileges on the system."

## CVSS Metrics

### CVSS v3.1

- Base Score: 7.8 (HIGH)
- Vector: CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H

### CVSS v2.0

- Base Score: 7.2 (HIGH)
- Vector: (AV:L/AC:L/Au:N/C:C/I:C/A:C)

## Weakness Classification

**CWE-665:** Improper Initialization

## Affected Software

Linux kernel versions:
- 5.8 through 5.10.102
- 5.15 through 5.15.25
- 5.16 through 5.16.11

Additional affected products include Red Hat Enterprise Linux (multiple versions), Fedora 35, and various hardware/firmware from NetApp, Siemens, and SonicWall.

## CISA Known Exploited Vulnerabilities

Included in CISA's Known Exploited Vulnerabilities Catalog (added 04/25/2022, due date 05/16/2022). Required action: Apply updates per vendor instructions.

## Publication Timeline

- NVD Published: 03/10/2022
- Last Modified: 11/06/2025
