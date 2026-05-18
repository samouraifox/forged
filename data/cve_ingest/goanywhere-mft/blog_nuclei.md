# CVE-2023-0669 - Fortra GoAnywhere MFT RCE (Nuclei Template Analysis)

**Source URL:** https://github.com/projectdiscovery/nuclei-templates/blob/main/http/cves/2023/CVE-2023-0669.yaml
**CVE:** CVE-2023-0669
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

**Vulnerability:** Fortra GoAnywhere MFT Remote Code Execution

**Core Issue:** The vulnerability stems from "unsafe deserialization of an arbitrary attacker-controlled object" combined with "pre-authentication command injection" in the License Response Servlet.

**Affected Product:** Fortra GoAnywhere Managed File Transfer (all versions prior to 7.1.2)

**Severity:** CVSS 3.1 score of 7.2 (High)

## HTTP Endpoint

- POST `/goanywhere/lic/accept`

## Request Structure

The template uses POST with `application/x-www-form-urlencoded` content type. The critical parameter is `bundle`, which contains:
- Base64-encoded encrypted payload
- AES-CBC encryption with a specified initialization vector
- Java gadget chain for DNS interaction
- URL encoding applied to the encrypted content

## Key Technical Components

- Encryption: AES/CBC/PKCS5Padding
- Gadget chain: Generated via `generate_java_gadget()` function
- Out-of-band testing: Uses DNS callbacks via Interactsh
- Expected response: HTTP 500 status with "GoAnywhere" in body

## CWE Classification

CWE-502 (Deserialization of Untrusted Data)

## EPSS Score

0.94378 (99.968th percentile - extremely exploitable)
