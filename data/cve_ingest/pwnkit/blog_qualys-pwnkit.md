# CVE-2021-4034 PwnKit — Qualys Security Advisory

**Source URL:** https://www.qualys.com/2022/01/25/cve-2021-4034/pwnkit.txt
**CVE:** CVE-2021-4034
**Fetched:** 2026-05-18
**Source type:** blog

Note: The canonical Qualys .txt advisory at this URL returned HTTP 404. Content below was retrieved from Qualys blog post at https://blog.qualys.com/vulnerabilities-threat-research/2022/01/25/pwnkit-local-privilege-escalation-vulnerability-discovered-in-polkits-pkexec-cve-2021-4034 and cross-referenced with NVD reference data.

---

## Title

"pwnkit: Local Privilege Escalation in polkit's pkexec (CVE-2021-4034)"

## Overview

This vulnerability enables "any unprivileged local user" to achieve root access through pkexec, a SUID-root program installed by default across major Linux distributions. The flaw has existed since pkexec's creation in May 2009.

## Affected Versions

"All versions of pkexec since its first version in May 2009" are vulnerable, affecting over a decade of deployments across Ubuntu, Debian, Fedora, and CentOS.

## Technical Analysis

### Vulnerability Mechanism

The vulnerability occurs when pkexec receives zero command-line arguments. The code attempts to process argv elements without bounds checking:

- Line 610 reads from out-of-bounds argv[1], actually accessing envp[0]
- Line 639 writes back to argv[1], overwriting the first environment variable
- This allows reinsertion of security-sensitive variables removed by ld.so

### Affected Code Location

Main function processes arguments (lines 534-568) and searches PATH directories (lines 610-640). The path discovery happens before environment variables are cleared at line 702.

When argc equals 0 (empty argument list):
- Line 534 sets integer n to 1
- Line 610 reads path pointer from argv[1] (actually envp[0])
- Line 639 writes processed path back to argv[1]

This out-of-bounds write overwrites the first environment variable, allowing attackers to "re-introduce an 'unsecure' environment variable (for example, LD_PRELOAD)" that SUID protections normally strip.

## Exploitation Method

The attack leverages GCONV_PATH, described as an "unsecure" environment variable. By manipulating this variable, attackers can force iconv_open() to load malicious shared libraries as root.

**The process:**
1. Create a directory structure containing a crafted executable
2. Set PATH to point there
3. Invoke pkexec with argc=0
4. This causes the out-of-bounds write to reintroduce GCONV_PATH

## Impact Assessment

- Affects Ubuntu, Debian, Fedora, CentOS, and other distributions
- "Exploitable instantly, reliably, in an architecture-independent way"
- Works even without the polkit daemon running
- Temporary mitigation: `chmod 0755 /usr/bin/pkexec`

Qualys QID 376287 tracks vulnerable instances across systems.

## Disclosure Timeline

- November 18, 2021: Advisory sent to Red Hat
- January 11, 2022: Advisory and patches distributed
- January 25, 2022: Coordinated release date (5:00 PM UTC)
