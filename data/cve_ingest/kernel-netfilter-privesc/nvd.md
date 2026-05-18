# CVE-2016-3134 - NVD Detail

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2016-3134
**CVE:** CVE-2016-3134
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Description
"The netfilter subsystem in the Linux kernel through 4.5.2 does not validate certain offset fields, which allows local users to gain privileges or cause a denial of service (heap memory corruption) via an IPT_SO_SET_REPLACE setsockopt call."

## CVSS Scores

**CVSS v3.0:**
- Base Score: 8.4 (HIGH)
- Vector: CVSS:3.0/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H

**CVSS v2.0:**
- Base Score: 7.2 (HIGH)
- Vector: (AV:L/AC:L/Au:N/C:C/I:C/A:C)

## Weakness Classification
- **CWE-119:** Improper Restriction of Operations within the Bounds of a Memory Buffer

## References
- Linux kernel commit: http://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=54d83fc74aa9ec72794373cb47432c5f7fb1a309
- GitHub mirror: https://github.com/torvalds/linux/commit/54d83fc74aa9ec72794373cb47432c5f7fb1a309
- Red Hat advisories: RHSA-2016-1847, RHSA-2016-1875, RHSA-2016-1883
- Debian security notice: http://www.debian.org/security/2016/dsa-3607
- Ubuntu USN notices: USN-2929-1, USN-2929-2, USN-2930-1 through USN-2930-3, USN-2931-1, USN-2932-1, USN-3049-1, USN-3050-1
- OpenSUSE advisories: Multiple 2016 security announcements (June-August)
- Oracle Linux bulletins: July and October 2016
- Security Tracker: http://www.securitytracker.com/id/1036763

## Technical Impact
Local privilege escalation and denial of service through heap memory corruption via netfilter socket operations.
