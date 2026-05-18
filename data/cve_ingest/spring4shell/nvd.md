# CVE-2022-22965 — Spring Framework JDK 9+ Remote Code Execution (Spring4Shell) — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2022-22965
**CVE:** CVE-2022-22965
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Title
Spring Framework JDK 9+ Remote Code Execution Vulnerability

## Description
"A Spring MVC or Spring WebFlux application running on JDK 9+ may be vulnerable to remote code execution (RCE) via data binding." The vulnerability specifically requires Tomcat WAR deployment; Spring Boot executable JAR deployments are not vulnerable, though other exploitation vectors may exist.

## CVSS Scores

**CVSS v3.1 (Critical):**
- Base Score: 9.8
- Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

**CVSS v2.0 (High):**
- Base Score: 7.5
- Vector: (AV:N/AC:L/Au:N/C:P/I:P/A:P)

## CWE Classification
CWE-94: Improper Control of Generation of Code ('Code Injection')

## Key Dates
- Published: 04/01/2022
- Last Modified: 10/30/2025

## Affected Software
Spring Framework versions:
- Prior to 5.2.20
- 5.3.0 through 5.3.17

Requires Oracle JDK 9 or later

## Notable References
- VMware Security Advisory: tanzu.vmware.com/security/cve-2022-22965
- CISA Known Exploited Vulnerabilities Catalog
- US-CERT: kb.cert.org/vuls/id/970766
- Cisco, Siemens, Oracle, and SonicWall advisories available
