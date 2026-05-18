# CVE-2022-22965 — Spring Framework RCE — Spring.io Vendor Advisory

**Source URL:** https://spring.io/security/cve-2022-22965
**CVE:** CVE-2022-22965
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

Note: tanzu.vmware.com/security/cve-2022-22965 redirects (301) to this URL.

---

## Vulnerability: Spring Framework Remote Code Execution via Data Binding on JDK 9+

**Severity:** CRITICAL
**Published:** March 31, 2022

## Description

"A Spring MVC or Spring WebFlux application running on JDK 9+ may be vulnerable to remote code execution (RCE) via data binding." The exploit specifically targets applications "packaged and deployed as a traditional WAR on a Servlet container," while Spring Boot executable JAR deployments remain unaffected.

## Prerequisites for Exploitation

- JDK 9 or higher
- Apache Tomcat as Servlet container
- WAR packaging
- spring-webmvc or spring-webflux dependency

## Affected Versions

- Spring Framework 5.3.0–5.3.17
- Spring Framework 5.2.0–5.2.19
- Older unsupported versions

## Fixed Versions

- Spring Framework 5.3.18+
- Spring Framework 5.2.20+

## Recommended Action

Users should upgrade to patched versions immediately. The advisory references a blog post with additional mitigation options for applications unable to upgrade promptly.

## Reporters

codeplutos and meizjm3i (AntGroup FG Security Lab), plus Praetorian
