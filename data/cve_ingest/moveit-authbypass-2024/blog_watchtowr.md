# CVE-2024-5806: MOVEit Transfer SFTP Authentication Bypass (watchTowr Labs)

**Source URL:** https://github.com/watchtowrlabs/CVE-2024-5806
**CVE:** CVE-2024-5806
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

CVE-2024-5806 affects Progress MOVEit Transfer and allows attackers to bypass SFTP authentication through log file poisoning.

## Vulnerability Details

**Type:** Authentication Bypass
**Affected Product:** Progress MOVEit Transfer
**Fixed Version:** 2024.0.2 and later

## Exploitation Mechanism

The exploit leverages a flaw in how MOVEit handles SFTP authentication. The attack involves "poisoning log files multiple times to be sure" before attempting authentication impersonation. The process includes:

1. Poisoning application log files repeatedly
2. Waiting for logs to flush to disk (60 seconds in the PoC)
3. Attempting SFTP authentication using a crafted server-side file path
4. Accessing target user files upon successful authentication

The example shows impersonating a user by referencing `'C:\MOVEitTransfer\Logs\DMZ_WEB.log'` as the authentication mechanism.

## Authors

The exploit was developed by Aliz Hammond and Sina Kheirkhah from watchTowr Labs, though they note they were not the original vulnerability discoverers.

## Resources

- Repository: watchtowr-vs-progress-moveit_CVE-2024-5806
- Contact: labs.watchtowr.com

## Clop Attribution Context (via BleepingComputer reporting)

The Clop ransomware gang claimed responsibility for exploiting zero-day vulnerabilities in Progress Software's MOVEit Transfer. Microsoft corroborated this, attributing the attacks to "Lace Tempest" (also known as TA505 and FIN11). The group stated they were "moving away from encryption and prefer data-theft extortion instead."

**Confirmed victims:**
- Zellis (UK payroll/HR provider)
- Aer Lingus
- British Airways (via Zellis infrastructure)
