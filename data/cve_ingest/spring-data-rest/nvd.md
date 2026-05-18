# CVE-2017-8046 — Spring Data REST PATCH RCE — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2017-8046
**CVE:** CVE-2017-8046
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Title
CVE-2017-8046

## Description
The vulnerability allows malicious PATCH requests to Spring Data REST servers to "run arbitrary Java code" through specially crafted JSON data. Affected versions include Spring Data REST prior to 2.6.9 (Ingalls SR9) and 3.0.1 (Kay SR1), plus Spring Boot versions before 1.5.9 and 2.0 M6.

## CVSS Scores

**CVSS v3.0 (Critical):**
- Base Score: 9.8
- Vector: CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

**CVSS v2.0 (High):**
- Base Score: 7.5
- Vector: (AV:N/AC:L/Au:N/C:P/I:P/A:P)

## CWE Classification
CWE-20: Improper Input Validation

## Key Dates
- Published: 01/04/2018
- Last Modified: 11/20/2024

## Affected Software
- Spring Data REST prior to 2.6.9 (Ingalls SR9)
- Spring Data REST prior to 3.0.1 (Kay SR1)
- Spring Boot versions before 1.5.9
- Spring Boot 2.0 M6

## Key References
- http://www.securityfocus.com/bid/100948
- https://access.redhat.com/errata/RHSA-2018:2405
- https://pivotal.io/security/cve-2017-8046
- https://www.exploit-db.com/exploits/44289/
