# VMSA-2022-0011 - VMware Security Advisory

**Source URL:** https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/23639
**CVE:** CVE-2022-22954
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

Note: Original VMware URL (https://www.vmware.com/security/advisories/VMSA-2022-0011.html) redirected 301 to Broadcom support portal.

## Advisory Metadata

- **Advisory ID:** VMSA-2022-0011.2
- **Status:** CLOSED
- **Severity:** CRITICAL
- **CVSS Range:** 5.3-9.8
- **Last Updated:** 05 September 2024
- **Initial Publication:** 04 April 2022

## Affected CVEs

Eight vulnerabilities identified: CVE-2022-22954, CVE-2022-22955, CVE-2022-22956, CVE-2022-22957, CVE-2022-22958, CVE-2022-22959, CVE-2022-22960, CVE-2022-22961

## Impacted Products

- VMware Workspace ONE Access
- VMware Identity Manager (vIDM)
- VMware vRealize Automation (vRA)
- VMware Cloud Foundation
- vRealize Suite Lifecycle Manager

## Key Vulnerabilities

**CVE-2022-22954** (CVSS 9.8 - Critical): "Server-side template injection" enabling remote code execution via network access. Confirmed active exploitation in the wild.

**CVE-2022-22955/22956** (CVSS 9.8 - Critical): OAuth2 ACS authentication bypass vulnerabilities in Workspace ONE Access only.

**CVE-2022-22957/22958** (CVSS 9.1 - Critical): JDBC injection RCE requiring administrative access; affects Access, Identity Manager, and vRealize Automation.

**CVE-2022-22959** (CVSS 8.8 - Important): Cross-site request forgery vulnerability.

**CVE-2022-22960** (CVSS 7.8 - Important): "Local privilege escalation" to root via improper support script permissions. Confirmed active exploitation.

**CVE-2022-22961** (CVSS 5.3 - Moderate): Information disclosure exposing hostname information.

## Remediation

Apply patches per KB88099. Workarounds documented in KB88098. Detailed FAQ: https://via.vmw.com/vmsa-2022-0011-qna
