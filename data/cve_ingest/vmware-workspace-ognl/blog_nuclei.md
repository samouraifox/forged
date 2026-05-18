# CVE-2022-22954 - VMware Workspace ONE Access SSTI (Nuclei Template Analysis)

**Source URL:** https://github.com/projectdiscovery/nuclei-templates/blob/main/http/cves/2022/CVE-2022-22954.yaml
**CVE:** CVE-2022-22954
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Description

"VMware Workspace ONE Access is susceptible to a remote code execution vulnerability due to a server-side template injection flaw."

## Affected Component

- **Product**: VMware Workspace ONE Access / Identity Manager
- **Vulnerable Version**: 3.3.3
- **Endpoint**: `/catalog-portal/ui/oauth/verify`

## Attack Vector

An unauthenticated attacker with network access can send specially crafted requests to exploit this vulnerability without authentication required.

## Technical Payload Details

The vulnerability exploits Freemarker template injection through the `deviceUdid` parameter. The encoded payload demonstrates command execution capability using Freemarker's utility functions.

**Affected Parameter**: `deviceUdid` (GET parameter)

**Injection Technique**: The vulnerability leverages `freemarker.template.utility.Execute` to achieve remote code execution through template processing.

**Example Command Context**: The payload demonstrates execution of system commands like `cat /etc/hosts`.

## Severity Metrics

- **CVSS Score**: 9.8 (Critical)
- **CVSS Metrics**: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
- **EPSS Score**: 0.94444 (99.992 percentile)
- **CWE**: CWE-94 (Improper Control of Generation of Code)

## Detection

The vulnerable endpoint responds with "Authorization context is not valid" error messages and HTTP 400 status codes.

## Impact

Successful exploitation enables complete system compromise affecting confidentiality, integrity, and availability.
