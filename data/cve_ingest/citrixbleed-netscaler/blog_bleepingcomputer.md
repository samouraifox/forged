# Citrix Bleed Exploit Lets Hackers Hijack NetScaler Accounts (BleepingComputer)

**Source URL:** https://www.bleepingcomputer.com/news/security/citrix-bleed-exploit-lets-hackers-hijack-netscaler-accounts/
**CVE:** CVE-2023-4966
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

CVE-2023-4966, known as "Citrix Bleed," is a critical-severity remotely exploitable information disclosure flaw affecting Citrix NetScaler ADC and NetScaler Gateway appliances. The vulnerability allows unauthenticated attackers to retrieve authentication session cookies from vulnerable devices.

## Timeline

- **August 2023**: Exploitation began as a zero-day
- **October 10, 2023**: Citrix released patches
- **October 17, 2023**: Mandiant disclosed active exploitation
- **October 23, 2023**: Citrix urged immediate patching
- **October 25, 2023**: Assetnote published proof-of-concept exploit and technical details

## Technical Details

### Root Cause

The vulnerability stems from a buffer over-read condition in two OpenID configuration functions: `ns_aaa_oauth_send_openid_config` and `ns_aaa_oauthrp_send_openid_config`. These functions employ `snprintf` to insert data into JSON payloads without proper bounds checking in unpatched versions.

The researchers found that "the hostname value used for generating the payload comes from the HTTP Host header, so one does not need administrator rights." Since the hostname is inserted six times into the response, attackers can exceed buffer limits and force the endpoint to leak adjacent memory contents.

### Affected Versions

- **Vulnerable**: NetScaler 13.1-48.47 (unpatched)
- **Patched**: NetScaler 13.1-49.15

## Exploitation Method

The patched version implements a critical check: "a response will only be sent if snprintf returns a value lower than 0x20000." This threshold prevents the buffer over-read in fixed releases.

Assetnote's testing revealed that through repeated exploitation attempts, attackers consistently locate "a 32-65 byte long hex string that is a session cookie," enabling unauthorized account hijacking and unrestricted appliance access.

## Impact & Response

Post-PoC publication, Shadowserver reported "spikes" in exploitation attempts. Given these vulnerabilities' historical use in ransomware and data theft campaigns, immediate patching is strongly recommended for system administrators.
