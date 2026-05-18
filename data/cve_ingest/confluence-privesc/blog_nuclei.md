# CVE-2023-22515 - Confluence Broken Access Control (Nuclei Template Analysis)

**Source URL:** https://github.com/projectdiscovery/nuclei-templates/blob/main/http/cves/2023/CVE-2023-22515.yaml
**CVE:** CVE-2023-22515
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

"Atlassian Confluence Data Center and Server contains a broken access control vulnerability that allows an attacker to create unauthorized Confluence administrator accounts."

## Severity & Impact

- **CVSS Score**: 9.8 (Critical)
- **CVSS Metrics**: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
- **EPSS Score**: 0.94326

The vulnerability enables unauthenticated attackers to gain complete administrative access to Confluence installations.

## Affected Endpoints

The exploit template targets these HTTP endpoints:

1. `/setup/setupadministrator-start.action` (GET)
2. `/server-info.action` (GET with parameter manipulation)
3. `/setup/setupadministrator.action` (POST - account creation)
4. `/dologin.action` (POST - authentication)
5. `/welcome.action` (GET - verification)

## Exploitation Steps

The attack workflow involves six HTTP requests:

1. **Initial setup check** via `/setup/setupadministrator-start.action`
2. **Bootstrap bypass** using `bootstrapStatusProvider.applicationConfig.setupComplete=0` parameter
3. **Setup page access** confirmation
4. **Admin account creation** via POST with form parameters (username, fullName, email, password)
5. **Account authentication** using created credentials
6. **Access verification** to confirm administrative privileges

## Key Technical Elements

- Uses `X-Atlassian-Token: no-check` header to bypass token validation
- Accepts form-urlencoded POST data for account creation
- Requires no prior authentication
- Includes parameter obfuscation using `cache{{randstr}}`

## CWE Classification

CWE-20: Improper Input Validation
