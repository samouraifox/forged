# Spring.io Security Advisory for CVE-2022-22963

**Source URL:** https://spring.io/security/cve-2022-22963
**CVE:** CVE-2022-22963
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability

Remote code execution in Spring Cloud Function through malicious Spring Expression Language (SpEL)

**Severity:** CRITICAL

**CVE ID:** CVE-2022-22963

**Publication Date:** March 29, 2022

## Affected Versions

Spring Cloud Function:
- 3.1.6
- 3.2.2
- Older unsupported versions

## Technical Details

"When using routing functionality it is possible for a user to provide a specially crafted SpEL as a routing-expression that may result in remote code execution and access to local resources."

## Remediation

**Fixed versions:**
- Spring Cloud Function 3.1.7
- Spring Cloud Function 3.2.3

Users require upgrade only; no additional mitigation steps necessary.

## Vulnerability Classification

- **CWE-770:** Allocation of Resources Without Limits or Throttling
- **CWE-497:** Exposure of Sensitive System Information to an Unauthorized Control Sphere

## CVSS v3.0 Score

Attack Vector: Network | Attack Complexity: Low | Privileges Required: None | User Interaction: None | Scope: Unchanged | Confidentiality Impact: High | Integrity Impact: High | Availability Impact: High

## Attribution

Initial discovery and responsible disclosure by m09u3r
