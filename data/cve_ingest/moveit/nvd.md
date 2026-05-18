# CVE-2023-34362 - NVD Entry

**Source URL:** https://nvd.nist.gov/vuln/detail/CVE-2023-34362
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-18
**Source type:** nvd

---

## Vulnerability Overview

CVE-2023-34362 is a critical SQL injection vulnerability affecting Progress MOVEit Transfer. The vulnerability allows unauthenticated attackers to compromise the application's database.

## Description

The flaw exists in MOVEit Transfer versions before specific patch releases: 2021.0.6, 2021.1.4, 2022.0.4, 2022.1.5, and 2023.0.1. An unauthenticated attacker can "gain access to MOVEit Transfer's database" and potentially "infer information about the structure and contents of the database, and execute SQL statements that alter or delete database elements" depending on which database engine is deployed.

The vulnerability was actively exploited in May and June 2023 via both HTTP and HTTPS connections.

## Severity Metrics

**CVSS v3.1 Score: 9.8 (CRITICAL)**
- Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`

## Weakness Classification

**CWE-89:** Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')

## References

- http://packetstormsecurity.com/files/172883/MOVEit-Transfer-SQL-Injection-Remote-Code-Execution.html
- http://packetstormsecurity.com/files/173110/MOVEit-SQL-Injection.html
- https://community.progress.com/s/article/MOVEit-Transfer-Critical-Vulnerability-31May2023
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog?field_cve=CVE-2023-34362

## CISA Requirements

Per CISA's BOD 22-01, affected organizations were required to apply vendor updates by June 23, 2023.
