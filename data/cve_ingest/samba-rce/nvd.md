# CVE-2017-7494 — Samba Remote Code Execution (SambaCry) — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2017-7494
**CVE:** CVE-2017-7494
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Title
Samba Remote Code Execution Vulnerability

## Description
"Samba since version 3.5.0 and before 4.6.4, 4.5.10 and 4.4.14 is vulnerable to remote code execution vulnerability, allowing a malicious client to upload a shared library to a writable share, and then cause the server to load and execute it."

## CVSS Scores

**CVSS v3.1 (NIST):**
- Base Score: 9.8 CRITICAL
- Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

**CVSS v2.0 (NIST):**
- Base Score: 10.0 HIGH
- Vector: (AV:N/AC:L/Au:N/C:C/I:C/A:C)

## Weakness Classification
CWE-94: Improper Control of Generation of Code ('Code Injection')

## Key Dates
- Published: 05/30/2017
- Last Modified: 04/21/2026
- CISA Added: 03/30/2023
- CISA Due: 04/20/2023

## Affected Versions
- Samba 3.5.0 through 4.3.x
- Samba 4.4.0 through 4.4.13
- Samba 4.5.0 through 4.5.9
- Samba 4.6.0 through 4.6.3

## Key References
- Samba Official Security Advisory: https://www.samba.org/samba/security/CVE-2017-7494.html
- Debian: http://www.debian.org/security/2017/dsa-3860
- Red Hat Advisories: RHSA-2017:1270, RHSA-2017:1271, RHSA-2017:1272, RHSA-2017:1273, RHSA-2017:1390
- Exploit-DB: https://www.exploit-db.com/exploits/42060/ and https://www.exploit-db.com/exploits/42084/
- CISA Known Exploited Vulnerabilities Catalog
