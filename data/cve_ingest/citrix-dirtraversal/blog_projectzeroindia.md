# CVE-2019-19781: Citrix ADC RCE - Project Zero India GitHub

**Source URL:** https://github.com/projectzeroindia/CVE-2019-19781
**CVE:** CVE-2019-19781
**Fetched:** 2026-05-18
**Source type:** blog

---

## Repository Overview

This repository contains a remote code execution exploit for Citrix Application Delivery Controller and Citrix Gateway (CVE-2019-19781).

**Usage:**
```
bash CVE-2019-19781.sh IP_OF_VULNERABLE_HOST COMMAND_TO_EXECUTE
```

**Example:**
```
bash CVE-2019-19781.sh XX.XX.XX.XX 'cat /etc/passwd'
```

## References Cited

- Citrix support article CTX267027
- NIST NVD entry for CVE-2019-19781
- MITRE CVE database entry

## EDB-47901 Technical Details (via exploit-db cross-reference)

**CVE ID:** CVE-2019-19781
**EDB ID:** 47901
**Type:** Remote Code Execution (RCE)
**Affected Software:** Citrix Application Delivery Controller and Citrix Gateway
**Release Date:** January 11, 2020
**Author:** Project Zero India

The proof-of-concept demonstrates a remote code execution vulnerability in Citrix's web application infrastructure. The attack leverages path traversal combined with template injection to achieve arbitrary command execution.

**Vulnerable endpoint:** `/vpn/../vpns/portal/scripts/newbm.pl`

The payload uses template processing to execute arbitrary commands via the `exec()` function, storing results in XML files within the portal directory.

**Attack Flow:**
1. Generates a random filename identifier
2. Sends crafted POST request with embedded template injection payload
3. Executes system command and writes output to temporary XML file
4. Retrieves command execution results via HTTP request

**Key Components:**
- **Vulnerable Parameter:** `url` parameter accepts template injection
- **Path Traversal:** Uses `NSC_USER` header for directory manipulation
- **Command Execution:** Leverages template processor's `exec()` function
