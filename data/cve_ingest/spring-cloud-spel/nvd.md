# NVD entry for CVE-2022-22963

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2022-22963
**CVE:** CVE-2022-22963
**Fetched:** 2026-05-18
**Source type:** nvd

---

## CVE ID

CVE-2022-22963

## Description

"When using routing functionality it is possible for a user to provide a specially crafted SpEL as a routing-expression that may result in remote code execution and access to local resources."

Affected: Spring Cloud Function versions 3.1.6, 3.2.2, and older unsupported versions.

## CVSS Scores

### CVSS v3.1

- Base Score: 9.8 CRITICAL
- Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

### CVSS v2.0

- Base Score: 7.5 HIGH
- Vector: (AV:N/AC:L/Au:N/C:P/I:P/A:P)

## Weakness Enumeration

| CWE-ID | CWE Name | Source |
|--------|----------|--------|
| CWE-917 | Improper Neutralization of Special Elements used in an Expression Language Statement | NIST |
| CWE-94 | Improper Control of Generation of Code ('Code Injection') | VMware |

## Affected Versions

- Spring Cloud Function versions up to and including 3.1.6
- Spring Cloud Function versions 3.2.0 through 3.2.2

## Key References

- VMware Security Advisory: https://tanzu.vmware.com/security/cve-2022-22963
- CISA Known Exploited Vulnerabilities Catalog
- Cisco Security Advisory
- Oracle Security Alerts (April and July 2022)
- SonicWall PSIRT Advisory

## CISA Status

Added to Known Exploited Vulnerabilities Catalog on 08/25/2022 with required action due by 09/15/2022: "Apply updates per vendor instructions."
