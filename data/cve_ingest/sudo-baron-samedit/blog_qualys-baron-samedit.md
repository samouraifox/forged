# CVE-2021-3156 Baron Samedit — Qualys Technical Analysis

**Source URL:** https://blog.qualys.com/vulnerabilities-threat-research/2021/01/26/cve-2021-3156-heap-based-buffer-overflow-in-sudo-baron-samedit
**CVE:** CVE-2021-3156
**Fetched:** 2026-05-18
**Source type:** blog

Note: The canonical Qualys .txt advisory at https://www.qualys.com/2021/01/26/cve-2021-3156/baron-samedit.txt returned HTTP 404. Content retrieved from the Qualys blog post at the URL above.

---

## Vulnerability Overview

A heap-based buffer overflow in sudo affects versions 1.8.2-1.8.31p2 and 1.9.0-1.9.5p1. According to the advisory, "any unprivileged user can gain root privileges on a vulnerable host using a default sudo configuration."

## Affected Versions

- Legacy versions: 1.8.2 to 1.8.31p2
- Stable versions: 1.9.0 to 1.9.5p1
- Vulnerability introduced July 2011 (commit 8255ed69)

## Technical Root Cause

The vulnerability exists in the `set_cmnd()` function within sudoers_policy_main(). The flaw occurs when processing arguments ending with a single backslash character. The code unescapes meta-characters but fails to account for out-of-bounds reads:

When a command-line argument ends with backslash, the unescape logic reads past the null terminator into adjacent memory, copying uncounted bytes to the heap-based "user_args" buffer.

## Exploitation Method

The attack requires executing `sudoedit -s` (not standard `sudo -s`). The vulnerability exists because:

- `sudoedit` automatically sets MODE_EDIT without resetting valid_flags
- MODE_SHELL remains in default valid_flags
- This combination bypasses the escape code in parse_args()
- Allows reaching vulnerable code in set_cmnd()

## Proof of Concept

```
sudoedit -s '\' `perl -e 'print "A" x 65536'`
```

This triggers: "malloc(): corrupted top size / Aborted (core dumped)"

## Attack Advantages

The attacker controls: buffer size, overflow contents, and can write null bytes to the overflowed buffer through environment variables or arguments ending with backslash.

## Detection Method

Run `sudoedit -s /` as non-root:
- Vulnerable: responds with error starting with "sudoedit:"
- Patched: responds with error starting with "usage:"

## Disclosure Timeline

- January 13, 2021: Advisory sent to Todd Miller
- January 19, 2021: Patches sent to distributions
- January 26, 2021: Coordinated public release (6:00 PM UTC)
