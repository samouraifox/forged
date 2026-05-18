# CVE-2023-22809 - OSS-Security Disclosure (Openwall)

**Source URL:** https://www.openwall.com/lists/oss-security/2023/01/19/1
**CVE:** CVE-2023-22809
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

## Mailing List Post

**From:** Matthieu Barjole <matthieu.barjole@synacktiv.com>

**Date:** Thursday, January 19, 2023 at 01:33:43 +0100

**Subject:** CVE-2023-22809: Sudoedit can edit arbitrary files

## Summary

Synacktiv researchers uncovered a privilege escalation flaw in sudoedit affecting "Sudo versions 1.8.0 through 1.9.12p1 inclusive." The vulnerability allows authorized users to modify files beyond their permitted scope.

## Technical Details

The vulnerability exploits how sudoedit processes editor environment variables. A user with restricted editing privileges can manipulate the EDITOR variable to target arbitrary files. For instance, if authorized only to edit `/etc/motd`, an attacker could execute:

```
EDITOR='vim -- /etc/passwd' sudoedit /etc/motd
```

to compromise system files.

## Remediation Options

**Immediate mitigation** involves deleting editor environment variables through sudoers configuration:

```
Defaults!sudoedit env_delete+="SUDO_EDITOR VISUAL EDITOR"
```

Command aliases can further refine restrictions for particular file editing scenarios:

```
Cmnd_Alias EDIT_MOTD = sudoedit /etc/motd
Defaults!EDIT_MOTD env_delete+="SUDO_EDITOR VISUAL EDITOR"
user ALL = EDIT_MOTD
```

## Resolution

The issue was resolved in Sudo version 1.9.12.p2.

## References
- Synacktiv security advisory
- Official Sudo security advisories at sudo.ws
- CVE-2023-22809 entry on MITRE

## Note
sudo.ws advisory URL https://www.sudo.ws/security/advisories/sudoedit_any/ returned HTTP 403 Forbidden and could not be fetched directly. The openwall oss-security post is the canonical public disclosure for this CVE.
