# Zero-Day Exploitation of Atlassian Confluence

**Source URL:** https://www.volexity.com/blog/2022/06/02/zero-day-exploitation-of-atlassian-confluence/
**CVE:** CVE-2022-26134
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

CVE-2022-26134 is "a zero-day vulnerability impacting fully up-to-date versions of Confluence Server" that enables unauthenticated remote code execution. The vulnerability was discovered during an incident response investigation in May 2022 and reported to Atlassian on May 31, 2022.

## Exploitation Details

**Vulnerability Type:** Command injection

The attack mechanism involved a single exploit attempt that "loaded a malicious class file in memory," enabling attackers to maintain webshell-like access without continuous re-exploitation or persistent file writes.

**Affected Versions:** All LTS versions and current versions such as 7.17.3 were confirmed vulnerable; "It is likely that all current versions of the product are impacted."

## Post-Exploitation Activity

Following initial compromise, attackers deployed:

1. **BEHINDER Implant** - An in-memory webshell providing "memory-only webshells and built-in support for interaction with Meterpreter and Cobalt Strike"

2. **noop.jsp** (File Upload Shell)
   - Size: 537 bytes
   - MD5: f8df4dd46f02dc86d37d46cf4793e036
   - Location: `<confluence_root>/confluence/noop.jsp`

3. **China Chopper JSP** (Default variant)
   - Size: 8624 bytes
   - MD5: ea18fb65d92e1f0671f23372bacf60e7

## Attacker Commands

Reconnaissance activities included OS enumeration, passwd/shadow file examination (/etc/passwd, /etc/shadow), database exploration, Confluence user table extraction, and log tampering to "remove evidence of exploitation."

## Attribution

Volexity identified 16 IP addresses and "reason to believe...the likely country of origin of these attackers is China." Multiple threat actors actively exploited this vulnerability.

## Detection Signatures

Suspicious POST requests to "/" index page with HTTP 200 responses may indicate exploitation activity.
