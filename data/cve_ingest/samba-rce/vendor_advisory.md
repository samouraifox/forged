# CVE-2017-7494 — SambaCry — Samba.org Official Security Advisory

**Source URL:** https://www.samba.org/samba/security/CVE-2017-7494.html
**CVE:** CVE-2017-7494
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

## Title

Remote code execution from a writable share

## CVE ID

CVE-2017-7494

## Affected Versions

"All versions of Samba from 3.5.0 onwards"

## Vulnerability Description

The flaw permits malicious clients to upload a shared library to a writable share and subsequently trigger server execution of that library. The mechanism exploits the ability to place executable files in writable locations that the Samba daemon subsequently loads.

## Patch Information

Security releases were issued as Samba 4.6.4, 4.5.10, and 4.4.14. Additional patches for older versions are available at http://samba.org/samba/patches/. The advisory recommends immediate upgrades or patch deployment.

Additional patch downloads: http://www.samba.org/samba/security/

## Workaround

Administrators can add `nt pipe support = no` to the [global] section of smb.conf and restart smbd. This restriction prevents client access to named pipes but may impact Windows client functionality.

## Credits

Steelo (knownsteelo@gmail.com) discovered the vulnerability; Volker Lendecke (SerNet) and the Samba Team developed the remediation.
