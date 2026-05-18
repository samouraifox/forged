# CVE-2019-18634 — Sudo Stack-Based Buffer Overflow via pwfeedback — NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2019-18634
**CVE:** CVE-2019-18634
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Title
Sudo Stack-Based Buffer Overflow via pwfeedback

## Description
This vulnerability affects Sudo versions before 1.8.26. When the `pwfeedback` option is enabled in `/etc/sudoers`, a local authenticated user can trigger a stack-based buffer overflow in the privileged sudo process by sending an excessively long string to stdin of the `getln()` function in `tgetpass.c`.

**Note:** While `pwfeedback` is enabled by default in Linux Mint and elementary OS, it is not standard in upstream distributions and requires administrator configuration.

## CVSS Scores

**CVSS v3.1 - Base Score: 7.8 (HIGH)**
- Vector: `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`

**CVSS v2.0 - Base Score: 4.6 (MEDIUM)**
- Vector: `(AV:L/AC:L/Au:N/C:P/I:P/A:P)`

## Weakness Classification
**CWE-787:** Out-of-bounds Write

## Key Dates
- Published: January 29, 2020
- Last Modified: November 20, 2024

## Affected Software
Sudo versions 1.7.1 through 1.8.25 (prior to 1.8.26)

## Key References
- **Vendor Alert:** https://www.sudo.ws/alerts/pwfeedback.html
- **Debian Security:** https://www.debian.org/security/2020/dsa-4614
- **Ubuntu Notices:** https://usn.ubuntu.com/4263-1/ and https://usn.ubuntu.com/4263-2/
- **Red Hat Advisories:** RHSA-2020:0487, RHSA-2020:0509, RHSA-2020:0540, RHSA-2020:0726
- **Gentoo Alert:** https://security.gentoo.org/glsa/202003-12
