# CVE-2021-26855 - Microsoft Security Blog: HAFNIUM Targeting Exchange Servers

**Source URL:** https://www.microsoft.com/en-us/security/blog/2021/03/02/hafnium-targeting-exchange-servers/
**CVE:** CVE-2021-26855
**Fetched:** 2026-05-18
**Source type:** blog

---

## Threat Actor Profile

HAFNIUM is a "state-sponsored" group "operating out of China" that primarily targets U.S. entities across sectors including law firms, defense contractors, and think tanks. The group "operates primarily from leased virtual private servers (VPS) in the United States."

## Vulnerabilities Exploited

Four CVEs were addressed in the March 2021 security update:

**CVE-2021-26855** (SSRF): "Server-side request forgery vulnerability in Exchange which allowed the attacker to send arbitrary HTTP requests and authenticate as the Exchange server."

**CVE-2021-26857** (Deserialization): "Insecure deserialization vulnerability in the Unified Messaging service" enabling code execution as SYSTEM, requiring admin permissions or another vulnerability.

**CVE-2021-26858** (File Write): "Post-authentication arbitrary file write vulnerability in Exchange" exploitable via CVE-2021-26855 SSRF or compromised credentials.

**CVE-2021-27065** (File Write): Similar post-authentication arbitrary file write capability.

## Attack Chain

Post-exploitation activities included:
- Deploying ASP web shells to enable data theft
- Using Procdump to extract LSASS memory
- Compressing data with 7-Zip for exfiltration
- Exporting mailbox data via Exchange PowerShell
- Deploying Nishang reverse shells and PowerCat remote access tools

## Detection Resources

Microsoft provided IOC feeds (CSV/JSON formats), web shell hashes, suspicious file paths, Azure Sentinel queries, and Microsoft Defender for Endpoint hunting queries to help organizations identify compromise.
