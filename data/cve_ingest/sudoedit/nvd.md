# CVE-2023-22809 - NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2023-22809
**CVE:** CVE-2023-22809
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Description
The sudoedit feature in Sudo versions 1.8.0 through 1.9.12.p1 has a flaw where it mishandles additional arguments passed through user environment variables (SUDO_EDITOR, VISUAL, EDITOR). This allows a local attacker to append arbitrary file entries to the processing list, potentially enabling privilege escalation. The vulnerability exploits how a user-specified editor containing a "--" argument can bypass protection mechanisms, such as: "EDITOR='vim -- /path/to/extra/file'".

## CVSS Metrics

**CVSS v3.1 (Base Score: 7.8 - HIGH)**
- Vector: `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`
- Sources: NIST, CISA-ADP

## Weakness Classification
- **CWE-269:** Improper Privilege Management

## Published
- **Published:** 01/18/2023
- **Last Modified:** 04/04/2025
- **Source:** MITRE

## References
- https://www.sudo.ws/security/advisories/sudoedit_any/
- https://www.debian.org/security/2023/dsa-5321
- https://support.apple.com/kb/HT213758
- https://www.synacktiv.com/sites/default/files/2023-01/sudo-CVE-2023-22809.pdf
- http://www.openwall.com/lists/oss-security/2023/01/19/1
- https://security.gentoo.org/glsa/202305-12
- https://security.netapp.com/advisory/ntap-20230127-0015/
