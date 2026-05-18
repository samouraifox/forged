# CVE-2021-3560 - NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2021-3560
**CVE:** CVE-2021-3560
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Description
"Polkit could be tricked into bypassing credential checks for D-Bus requests, elevating requestor privileges to root." This flaw allows unprivileged local attackers to create new administrators, threatening data confidentiality, integrity, and system availability.

## CVSS Scores & Vectors

**CVSS 3.1 (NIST & CISA-ADP):**
- Base Score: 7.8 HIGH
- Vector: `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`

**CVSS 2.0 (NIST):**
- Base Score: 7.2 HIGH
- Vector: `(AV:L/AC:L/Au:N/C:C/I:C/A:C)`

## Weakness Classification
- **CWE-754:** Improper Check for Unusual or Exceptional Conditions (NIST)
- **CWE-863:** Incorrect Authorization (Red Hat, Inc.)

## References
- http://packetstormsecurity.com/files/172836/polkit-Authentication-Bypass.html
- http://packetstormsecurity.com/files/172846/Facebook-Fizz-Denial-Of-Service.html
- https://bugzilla.redhat.com/show_bug.cgi?id=1961710
- https://github.blog/2021-06-10-privilege-escalation-polkit-root-on-linux-with-bug/
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2021-3560

## CISA Status
Listed in CISA's Known Exploited Vulnerabilities Catalog with action required by 06/02/2023: "Apply updates per vendor instructions."
