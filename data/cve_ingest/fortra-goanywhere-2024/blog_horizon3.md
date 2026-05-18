# CVE-2024-0204 - Fortra GoAnywhere MFT Authentication Bypass (Horizon3 Analysis)

**Source URL:** https://www.horizon3.ai/attack-research/disclosures/goanywhere-mft-cve-2024-0204-authentication-bypass/
**CVE:** CVE-2024-0204
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

CVE-2024-0204 is an authentication bypass vulnerability in Fortra GoAnywhere MFT that "allows an unauthenticated attacker to create an administrative user for the application."

## Affected Component

The vulnerable endpoint is `/InitialAccountSetup.xhtml`, mapped to the `com.linoma.ga.ui.admin.users.InitialAccountSetupForm` class in the `gamft-7.4.0.jar` library.

## Exploitation Technique

The bypass exploits a **path normalization vulnerability** using Tomcat-style path traversal. The attacker requests:
```
/goanywhere/images/..;/wizard/InitialAccountSetup.xhtml
```

This `/..;/` sequence bypasses the `SecurityFilter` class's `doFilter()` method, which checks the request path. The filter fails to properly validate normalized paths, allowing access to the setup page even when an admin user already exists.

## Technical Mechanism

- **Normal logic**: The `SecurityFilter` class redirects authenticated requests to `/wizard/InitialAccountSetup.xhtml` away from setup
- **Bypass**: Path traversal tricks the filter into treating the request as a different path, routing it to the vulnerable setup form
- **Result**: The attacker submits the form with path traversal applied, creating a new administrative user

## Indicators of Compromise

- Unexpected admin users in the "Admin Users" section
- Database transaction logs at `\GoAnywhere\userdata\database\goanywhere\log\*.log` showing user additions

## Mitigation

Delete `/InitialAccountSetup.xhtml` and restart the service.

## CVSS

- **CVSS 3.1 Base Score**: 9.8 (CRITICAL)
- **Vector**: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
- **CWE**: CWE-425 (Direct Request / Forced Browsing)
