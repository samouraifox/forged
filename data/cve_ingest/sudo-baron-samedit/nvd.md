# CVE-2021-3156 — Sudo Heap-Based Buffer Overflow (Baron Samedit) — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2021-3156
**CVE:** CVE-2021-3156
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Basic Information
- **CVE ID:** CVE-2021-3156
- **Published:** January 26, 2021
- **Last Modified:** November 10, 2025
- **Source:** MITRE

## Description
"Sudo before 1.9.5p2 contains an off-by-one error that can result in a heap-based buffer overflow, which allows privilege escalation to root via 'sudoedit -s' and a command-line argument that ends with a single backslash character."

## CVSS Metrics

**CVSS v3.1 - Base Score: 7.8 (HIGH)**
- Vector: `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`

**CVSS v2.0 - Base Score: 7.2 (HIGH)**
- Vector: `(AV:L/AC:L/Au:N/C:C/I:C/A:C)`

## Weakness
**CWE-193:** Off-by-one Error

## Affected Software
- Sudo versions before 1.9.5p2
- Includes versions 1.8.2 through 1.8.31p2 and 1.9.0 through 1.9.5p1
- Multiple Linux distributions and other operating systems

## CISA Known Exploited Vulnerabilities
- **Added:** April 6, 2022
- **Due Date:** April 27, 2022
- **Required Action:** "Apply updates per vendor instructions."

## Key References
- Sudo official release: https://www.sudo.ws/stable.html#1.9.5p2
- CERT advisory: https://www.kb.cert.org/vuls/id/794544
- Multiple security advisories from Debian, Fedora, Gentoo, Cisco, Apple, and NetApp available in reference list
