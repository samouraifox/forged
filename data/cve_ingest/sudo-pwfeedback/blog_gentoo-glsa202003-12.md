# CVE-2019-18634 sudo pwfeedback — Gentoo GLSA 202003-12

**Source URL:** https://security.gentoo.org/glsa/202003-12
**CVE:** CVE-2019-18634
**Fetched:** 2026-05-18
**Source type:** blog

---

## Advisory: GLSA 202003-12

**Affected Package:** app-admin/sudo (all architectures)
**Affected Versions:** < 1.8.31
**Fixed Version:** >= 1.8.31
**Release Date:** March 14, 2020

## Description

CVE-2019-18634 is listed as one of the vulnerabilities addressed in this advisory. Multiple vulnerabilities have been discovered in sudo. The advisory states: "Multiple vulnerabilities have been discovered in sudo. Please review the CVE identifiers referenced below for details."

## Overall Impact

The advisory indicates the overall impact includes: "expose or corrupt memory information, inject code to be run as a root user or cause a Denial of Service condition"

## Exploitability

- Local
- Severity: High

## Additional Context from NVD

When the `pwfeedback` option is enabled in `/etc/sudoers`, a local authenticated user can trigger a stack-based buffer overflow in the privileged sudo process by sending an excessively long string to stdin of the `getln()` function in `tgetpass.c`.

Affected versions: Sudo 1.7.1 through 1.8.25 (prior to 1.8.26).

Upstream patch commit: fa8ffeb17523494f0e8bb49a25e53635f4509078
