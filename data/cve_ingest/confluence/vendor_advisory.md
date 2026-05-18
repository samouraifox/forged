# Confluence Security Advisory 2022-06-02

**Source URL:** https://confluence.atlassian.com/doc/confluence-security-advisory-2022-06-02-1130377146.html
**CVE:** CVE-2022-26134
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

**CVE ID:** CVE-2022-26134
**Severity:** Critical
**Vulnerability Type:** OGNL injection enabling unauthenticated remote code execution

## Affected Products & Versions

**Products:**
- Confluence Server
- Confluence Data Center

**Affected Versions:** "All supported versions of Confluence Server and Data Center are affected" and versions after 1.3.0

## Fixed Versions
- 7.4.17
- 7.13.7
- 7.14.3
- 7.15.2
- 7.16.4
- 7.17.4
- 7.18.1

## Vulnerability Description

"The OGNL injection vulnerability allows an unauthenticated user to execute arbitrary code on a Confluence Server or Data Center instance."

## Mitigation Steps

**For Confluence 7.15.0-7.18.0:**
1. Shut down Confluence
2. Download: `xwork-1.0.3-atlassian-10.jar`
3. Delete: `<confluence-install>/confluence/WEB-INF/lib/xwork-1.0.3-atlassian-8.jar`
4. Copy downloaded JAR to `<confluence-install>/confluence/WEB-INF/lib/`
5. Verify permissions match existing files
6. Restart Confluence

**For Confluence 6.0.0-7.14.2:**
Download three files: `xwork-1.0.3-atlassian-10.jar`, `webwork-2.1.5-atlassian-4.jar`, and `CachedConfigurationProvider.class`. Remove old JARs and place new files in appropriate directories with correct permissions.

## Key Notes
- Atlassian Cloud (atlassian.net) is protected
- Clustering requires per-node mitigation application
- Binary patches are no longer released per policy
