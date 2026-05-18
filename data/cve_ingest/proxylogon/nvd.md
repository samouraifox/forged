# CVE-2021-26855 - NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2021-26855
**CVE:** CVE-2021-26855
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Description
"Microsoft Exchange Server Remote Code Execution Vulnerability" affecting multiple versions of Microsoft Exchange Server.

## CVSS Scores

**CVSS v3.1:**
- NIST Base Score: 9.8 (CRITICAL)
- Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`

- Microsoft Base Score: 9.1 (CRITICAL)
- Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N`

**CVSS v2.0:**
- NIST Base Score: 7.5 (HIGH)
- Vector: `(AV:N/AC:L/Au:N/C:P/I:P/A:P)`

## Weakness Classification
**CWE-918:** Server-Side Request Forgery (SSRF)

## Affected Software
- Microsoft Exchange Server 2013 (CU 21-23)
- Microsoft Exchange Server 2016 (CU 8-19)
- Microsoft Exchange Server 2019 (all versions through CU 8)

## References

| URL | Type |
|-----|------|
| https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/CVE-2021-26855 | Patch, Vendor Advisory |
| http://packetstormsecurity.com/files/161846/Microsoft-Exchange-2019-SSRF-Arbitrary-File-Write.html | Exploit, Third Party Advisory |
| http://packetstormsecurity.com/files/161938/Microsoft-Exchange-ProxyLogon-Remote-Code-Execution.html | Exploit, Third Party Advisory |
| http://packetstormsecurity.com/files/162610/Microsoft-Exchange-2019-Unauthenticated-Email-Download.html | Exploit, Third Party Advisory |
| http://packetstormsecurity.com/files/162736/Microsoft-Exchange-ProxyLogon-Collector.html | Exploit, Third Party Advisory |
| https://www.cisa.gov/known-exploited-vulnerabilities-catalog | Government Resource |

## CISA Status
Listed in Known Exploited Vulnerabilities Catalog with required remediation action: "Apply updates per vendor instructions" (Due date: 05/03/2022)
