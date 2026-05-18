# CVE-2023-34362: MOVEit Transfer Critical Vulnerability - Huntress Rapid Response

**Source URL:** https://www.huntress.com/blog/moveit-transfer-critical-vulnerability-rapid-response
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

On May 31, 2023, Progress disclosed a critical vulnerability in MOVEit Transfer that enables unauthorized access through SQL injection. Active exploitation began immediately, with the vulnerability designated **CVE-2023-34362** on June 2, 2023.

## Technical Details

### Vulnerability Mechanism

The flaw exploits SQL injection via the `moveitisapi.dll` component when accessed with specific HTTP headers. Attackers can inject malicious SQL commands to bypass authentication and gain administrative privileges.

### Attack Chain

Huntress documented the exploitation sequence:
1. Initial reconnaissance via GET requests to the application root
2. Session preparation through `guestaccess.aspx` to extract CSRF tokens
3. SQL injection payload delivery via `moveitisapi/moveitisapi.dll`
4. C# compilation via `w3wp.exe` to create a malicious ASPX backdoor
5. Persistence through a staged webshell file

### Arbitrary Code Execution

Beyond file exfiltration, the vulnerability enables "arbitrary code execution" with `moveitsvc` account privileges (administrator group member). This allows attackers to disable antivirus and deploy ransomware immediately.

## Key Indicators of Compromise (IOCs)

**Files:**
- `C:\MOVEitTransfer\wwwroot\human2.aspx` (webshell backdoor)
- `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\Temporary ASP.NET Files\root\` (compiled DLL artifacts)

**IP Addresses:**
- 89.39.105.108, 5.252.190.0/24, 5.252.189-195.x ranges
- 148.113.152.144, 138.197.152.201, 209.97.137.33

**Process Indicators:**
- `w3wp.exe` executing `csc.exe` (C# compiler)
- Multiple `App_Web_*.dll` files in temporary ASP.NET directories

## Detection Methods

**Log Analysis:**
Monitor IIS access logs for POST requests to `/guestaccess.aspx`, `/api/v1/token`, and `/moveitisapi/moveitisapi.dll` with suspicious header patterns.

**YARA Rules:**
Huntress released detection rules targeting the `human2.aspx` webshell, including a distinctive variable misspelling: `azureAccout` instead of `azureAccount`.

**Sigma Rules:**
Community-contributed rules detect suspicious file creation, IIS anomalies, and malicious DLL compilation in temporary ASP.NET directories.

## Mitigation Steps

**Immediate Actions:**
1. Update to patched versions:
   - MOVEit Transfer 2023.0.1
   - 2022.1.5, 2022.0.4, 2021.1.4, 2021.0.6
2. Alternative: Implement firewall deny rules blocking ports 80/443 (disables the application)
3. Enable comprehensive logging for investigation

**Investigation Resources:**
- Registry key: `HKEY_LOCAL_MACHINE\SOFTWARE\Standard Networks\siLock` contains configuration paths
- Log files location: `LogsBaseDir` registry value
- Database configuration: MySQL settings under `siLock\MySQL`, MSSQL settings under `siLock\SQLServer`

## Attribution

Microsoft attributed the exploitation to "Lace Tempest," the threat group operating cl0p ransomware, linking this to previous MFT software attacks (GoAnywhere).

## Related CVE

**CVE-2023-35036** addressed additional SQL injection vectors enabling database exfiltration and was released June 12, 2023.
