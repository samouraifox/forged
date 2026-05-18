# CVE-2019-18634 — sudo pwfeedback — sudo.ws Vendor Alert

**Source URL:** https://www.sudo.ws/alerts/pwfeedback.html
**CVE:** CVE-2019-18634
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

Note: https://www.sudo.ws/alerts/pwfeedback.html and https://www.sudo.ws/security/advisories/pwfeedback/ both returned HTTP 403. The canonical vendor alert URL is listed in NVD references. Ubuntu security tracker content was successfully fetched and confirms the same technical information.

---

## Source: Ubuntu Security Tracker for CVE-2019-18634

**Source URL used:** https://ubuntu.com/security/CVE-2019-18634

## Description

"In Sudo before 1.8.26, if pwfeedback is enabled in /etc/sudoers, users can trigger a stack-based buffer overflow in the privileged sudo process." The vulnerability requires delivering a lengthy string to stdin of getln() in tgetpass.c. Notably, pwfeedback defaults to enabled in Linux Mint and elementary OS but remains disabled in upstream Ubuntu.

## Affected Versions

- Sudo 1.7.1 through 1.8.25p1 (prior to 1.8.26)

## CVSS 3.1 Score

- Score: 7.8 (High)
- Vector: CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H

## Ubuntu Fixes

- 19.10 (eoan): Fixed in 1.8.27-1ubuntu4.1
- 18.04 LTS (bionic): Fixed in 1.8.21p2-3ubuntu1.2
- 16.04 LTS (xenial): Fixed in 1.8.16-0ubuntu1.9
- 14.04 LTS (trusty): ESM fix available

## Key References

- Upstream patch commit: fa8ffeb17523494f0e8bb49a25e53635f4509078
- USN-4263-1 and USN-4263-2
- Published: 31 January 2020
