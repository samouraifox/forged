# CVE-2023-0669 - NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2023-0669
**CVE:** CVE-2023-0669
**Fetched:** 2026-05-18
**Source type:** nvd

---

**CVE ID:** CVE-2023-0669

**Description:** A pre-authentication command injection vulnerability exists in Fortra GoAnywhere MFT's License Response Servlet. The flaw stems from "deserializing an arbitrary attacker-controlled object." Version 7.1.2 and later contain the fix.

**CVSS Scores:**
- CVSS v3.1: Base Score 7.2 (HIGH)
- Vector: CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H
- CVSS v4.0: Not yet assessed by NIST
- CVSS v2.0: Not assessed

**CWE:** CWE-502 (Deserialization of Untrusted Data)

**Affected Versions:** GoAnywhere Managed File Transfer versions prior to 7.1.2

**Publication Date:** February 6, 2023

**Last Modified:** November 3, 2025

**Known Exploited:** Yes—listed in CISA's Known Exploited Vulnerabilities Catalog with due date March 3, 2023

**Key References:**
- Rapid7 analysis and Metasploit module
- Fortra security advisory
- Packet Storm Security exploit documentation
- CISA vulnerability catalog entry
