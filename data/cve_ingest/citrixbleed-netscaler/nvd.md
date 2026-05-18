# CVE-2023-4966 - NVD Entry

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2023-4966
**CVE:** CVE-2023-4966
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Vulnerability Description

Sensitive information disclosure in NetScaler ADC and NetScaler Gateway when configured as a Gateway (VPN virtual server, ICA Proxy, CVPN, RDP Proxy) or AAA virtual server.

## CVSS Scores

- **NIST (CVSS 3.1)**: Base Score 7.5 HIGH
  - Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`

- **Citrix Systems, Inc. (CVSS 3.1)**: Base Score 9.4 CRITICAL
  - Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L`

## Weakness Classification

- **CWE-119**: Improper Restriction of Operations within the Bounds of a Memory Buffer
- **CWE-NVD-noinfo**: Insufficient Information

## References

1. http://packetstormsecurity.com/files/175323/Citrix-Bleed-Session-Token-Leakage-Proof-Of-Concept.html (Third Party Advisory, VDB Entry)
2. https://support.citrix.com/article/CTX579459 (Vendor Advisory)
3. https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2023-4966 (US Government Resource)

## CISA Status

This vulnerability is listed in CISA's Known Exploited Vulnerabilities Catalog with a due date of 11/08/2023, requiring mitigation application and session termination per vendor instructions or product discontinuation.

## Timeline

- **Published:** October 10, 2023
- **Last Modified:** (as of fetch date)
