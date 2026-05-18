# CVE-2023-29298 - Adobe ColdFusion Access Control Bypass (Nuclei Template Analysis)

**Source URL:** https://github.com/projectdiscovery/nuclei-templates/blob/main/http/cves/2023/CVE-2023-29298.yaml
**CVE:** CVE-2023-29298
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

**Adobe ColdFusion Access Control Bypass** affects ColdFusion 2021 Update 6 and allows attackers to bypass authentication protections on the administrator interface.

## Description

The vulnerability enables unauthorized access to CFM and CFC files within "/CFIDE/" paths. "An attacker is able to access every CFM and CFC endpoint within the ColdFusion Administrator path /CFIDE/" — approximately 437 CFM files and 96 CFC files in affected installations.

## HTTP Request Template

```
GET {{BaseURL}}//CFIDE/wizards/common/utils.cfc?method=wizardHash&inPassword=foo&_cfclient=true&returnFormat=wddx
```

## Detection Indicators

The successful exploitation returns:
- HTTP Status: 200
- Content-Type: text/html
- Body pattern: Three 32-character hexadecimal values separated by commas (regex: `(\[0-9a-fA-F\]{32},){2}\[0-9a-fA-F\]{32}`)
- Response length: 106 characters (trimmed)

## Severity Metrics

- **CVSS 3.1**: 7.5 (High)
- **CWE**: CWE-284, NVD-CWE-Other
- **EPSS Score**: 0.9429 (99.943rd percentile)

## Impact

The bypass allows information disclosure through unauthorized administrative endpoint access without requiring valid credentials. Approximately 437 CFM files and 96 CFC files within the `/CFIDE/` path are accessible.
