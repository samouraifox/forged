# CVE-2017-8046 — Spring Data REST PATCH RCE — Spring.io Vendor Advisory

**Source URL:** https://spring.io/security/cve-2017-8046
**CVE:** CVE-2017-8046
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

Note: pivotal.io/security/cve-2017-8046 returned certificate expired error; spring.io/security/cve-2017-8046 is the current canonical location for this advisory.

---

## Title
RCE in PATCH requests in Spring Data REST

**Severity:** CRITICAL
**Published:** September 21, 2017

## Description

The vulnerability allows attackers to "use specially crafted JSON data to run arbitrary Java code" through malicious PATCH requests to Spring Data REST servers.

## Affected Versions

- Spring Data REST: versions before 2.6.9 (Ingalls SR9) and 3.0.1 (Kay SR1)
- Spring Boot: versions before 1.5.9 and 2.0 M6

## Fixed Versions

- Spring Data REST 2.6.9 (October 27, 2017)
- Spring Data REST 3.0.1 (October 27, 2017)
- Spring Boot 1.5.9 (October 28, 2017)
- Spring Boot 2.0 M6 (November 6, 2017)

## Credit

Man Yue Mo (Semmle and lgtm.com)

## References

- JIRA DATAREST-1127
- JIRA DATAREST-1152

## Timeline Note

Initial report published September 21, 2017; affected/fixed versions corrected March 6, 2018.
