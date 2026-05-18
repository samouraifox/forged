# CVE-2022-27510 - NVD Entry

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2022-27510
**CVE:** CVE-2022-27510
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Vulnerability Details

**Description:** "Unauthorized access to Gateway user capabilities"

**Severity:** CRITICAL (CVSS 9.8)

**CVSS 3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`

## Affected Products

- Citrix Gateway versions 12.1 through 13.1 (specific version ranges)
- Citrix Application Delivery Controller (ADC) firmware versions 12.1 through 13.1

## Weakness Classification

- **CWE-287:** Improper Authentication
- **CWE-288:** Authentication Bypass Using an Alternate Path or Channel

## References

- **Vendor Advisory:** https://support.citrix.com/article/CTX463706/citrix-gateway-and-citrix-adc-security-bulletin-for-cve202227510-cve202227513-and-cve202227516

## Key Dates

- **Published:** November 8, 2022
- **Last Modified:** November 21, 2024

## Impact

The vulnerability allows network-accessible unauthorized access to Gateway user functions without requiring authentication, credentials, or user interaction, resulting in potential compromise of confidentiality, integrity, and availability.
