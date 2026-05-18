# CVE-2023-34362 MOVEit Transfer Vulnerability - Horizon3 Attack Team

**Source URL:** https://github.com/horizon3ai/CVE-2023-34362
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

Proof-of-concept exploit for CVE-2023-34362, affecting MOVEit Transfer. The vulnerability chain combines two critical flaws to achieve remote code execution.

## Technical Details

**Attack Chain:**
The exploit abuses "an SQL injection to obtain a sysadmin API access token and then use that access to abuse a deserialization call to obtain remote code execution."

**Key Components:**
- **SQL Injection**: Used to extract administrative credentials/tokens
- **Deserialization Vulnerability**: Leveraged after authentication to execute arbitrary code
- **Identity Provider Integration**: The PoC contacts an IDP endpoint to obtain RS256 certificates for forging user tokens

## Exploitation Process

The tool performs the following steps:

1. Retrieves sysadmin access token via SQL injection
2. Obtains a Folder ID from the system
3. Uploads a malicious file
4. Injects payload into the uploaded file
5. Triggers execution through a resume operation
6. Cleans up by deleting the uploaded file

**Default Payload**: Writes output to `C:\Windows\Temp\message.txt`. Custom payloads can be generated using ysoserial.net.

## Mitigation

Update to the latest version or mitigate by following the instructions within the Progress Advisory at the community portal.

## Resources

- Technical analysis available via Horizon3.ai's blog
- Created by the Horizon3 Attack Team for defensive research purposes
