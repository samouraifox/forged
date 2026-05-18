# ProxyShell Chain - Zero Day Initiative Technical Writeup

**Source URL:** https://www.zerodayinitiative.com/blog/2021/8/17/from-pwn2own-2021-a-new-attack-surface-on-microsoft-exchange-proxyshell
**CVE:** CVE-2021-34473, CVE-2021-34523, CVE-2021-31207
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

ProxyShell represents a three-vulnerability exploit chain enabling unauthenticated remote code execution against Microsoft Exchange Server through port 443.

## CVE-2021-34473: Path Confusion & ACL Bypass

The first flaw exploits URL normalization in the Client Access Services layer. When processing Explicit Logon requests, the system fails to properly validate mailbox addresses provided via query parameters.

The researchers crafted a malicious URL structure:

```
https://exchange/autodiscover/autodiscover.json?@foo.com/?&Email=autodiscover/autodiscover.json%3f@foo.com
```

This allowed them to access "arbitrary backend URLs while running as the Exchange Server machine account," bypassing access controls despite being unauthenticated.

## CVE-2021-34523: PowerShell Elevation of Privilege

The path confusion vulnerability alone grants limited access. The researchers discovered that when the PowerShell backend receives requests without a valid authentication header, it attempts to restore user identity from an `X-Rps-CAT` query parameter.

This parameter restoration mechanism, "designed for internal Exchange PowerShell intercommunication," could be abused to impersonate administrative accounts. The team used this to escalate from SYSTEM (lacking mailbox privileges) to Exchange Admin status.

## CVE-2021-31207: Arbitrary File Write to RCE

With admin credentials, the `New-MailboxExportRequest` cmdlet exports mailboxes to arbitrary file paths. The payload delivery strategy involved:

1. **Encoding phase**: Delivering a web shell through SMTP with Permutative Encoding matching the PST format
2. **Export execution**: Exporting the crafted mailbox to the web root
3. **Bypass technique**: Copying `cmd.exe` to a randomized filename to evade Windows Defender

## Complete Attack Flow

The exploitation sequence: malicious payload delivery via SMTP → PowerShell session hijacking with identity spoofing → role assignment and mailbox export → web shell execution with filename obfuscation.

## Source Note

devco.re blog URLs for ProxyShell (https://devco.re/blog/2021/08/06/proxyshell-poc/) returned HTTP 404. Content above is from ZDI blog post.
