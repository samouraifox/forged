# Zero-Day Vulnerability in MOVEit Transfer Exploited for Data Theft (Mandiant/Google Cloud)

**Source URL:** https://cloud.google.com/blog/topics/threat-intelligence/zero-day-moveit-data-theft/
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-18
**Source type:** blog

---

## Summary

Mandiant discovered widespread exploitation of CVE-2023-34362, a zero-day vulnerability in MOVEit Transfer secure file transfer software. The earliest exploitation occurred on May 27, 2023, with data theft happening within minutes of web shell deployment.

## Key Technical Details

### LEMURLOOT Web Shell

- **Language**: C# ASP.NET web shell
- **Filenames**: `human.aspx`, `human2.aspx`, `_human2.aspx` (masquerading as legitimate MOVEit components)
- **Authentication**: Hard-coded 36-character GUID in `X-siLock-Comment` HTTP header
- **Response**: Returns `X-siLock-Comment` header with value "comment" on successful authentication

### Command Structure

LEMURLOOT parses commands via HTTP headers:

**X-siLock-Step1 Commands:**
- `-1`: Retrieves Azure system settings (`AzureBlobStorageAccount`, `AzureBlobKey`, `AzureBlobContainer`) and SQL queries for file/folder enumeration
- `-2`: Deletes user with `LoginName`/`RealName` = "Health Check Service"

**X-siLock-Step2 & Step3:**
- Parse `fileid` and `folderid` values to retrieve specific files
- Creates temporary account with name "Health Check Service" if needed
- Data returned is gzip compressed

### Attack Infrastructure

- Scanning/exploitation sourced from IP range: **5.252.188.0/22**
- Secondary operations from different systems with RDP certificates generated May 19-22, 2023

## Attribution

- **Initial**: UNC4857
- **Updated**: Merged into **FIN11** based on targeting, infrastructure, certificates, and data leak site overlaps
- **Data Leak Site**: `CL0P^_-LEAKS` (claimed responsibility June 6, 2023)
- **Ransomware Association**: CLOP ransomware group

## YARA Detection Rules

Two rules provided for hunting:
1. **M_Webshell_LEMURLOOT_DLL_1**: Detects compiled DLLs from human2.aspx payloads (filesize < 15KB)
2. **M_Webshell_LEMURLOOT_1**: Detects ASP.NET scripts (5-10KB filesize)

Key detection strings include:
- `"X-siLock-Comment"`, `"X-siLock-Step2"`, `"X-siLock-Step3"`
- `"Health Check Service"`
- `"attachment; filename={0}"`

## Indicators of Compromise

The blog post includes 40 file hashes (MD5 and SHA256) for LEMURLOOT samples, the first appearing on VirusTotal May 28, 2023.

## Impact

- Organizations in Canada, India, and U.S. confirmed impacted
- Samples uploaded from Italy, Pakistan, and Germany
- Data theft occurred from Azure Blob Storage in some cases
- No initial ransom demands; threats posted to data leak site after June 6

## Resources

Mandiant provided:
- MOVEit Containment and Hardening guide
- Mandiant Security Validation actions (6 validation IDs provided)
- CAMP.23.037 tracking page in Mandiant Advantage
