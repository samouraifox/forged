# MOVEit Transfer RCE Part Two (CVE-2023-34362) — AssetNote Research

**Source URL:** https://www.assetnote.io/resources/research/moveit-transfer-rce-part-two-cve-2023-34362
**CVE:** CVE-2023-34362
**Fetched:** 2026-05-19
**Source type:** blog

---

## Summary

Operator-grade reverse-engineering of the MOVEit Transfer CVE-2023-34362 SQLi-to-RCE chain. The exploitation flow chains header smuggling, unsanitized session-variable injection, second-order SQL injection in `guestaccess.aspx`, federated-authentication abuse, and unsafe `BinaryFormatter` deserialization to achieve unauthenticated RCE. Attributed to the **Cl0p ransomware** group via Mandiant and Microsoft.

---

## Vulnerable Endpoints

```
/MOVEitISAPI/MOVEitISAPI.dll?action=m2
/machine2.aspx
/guestaccess.aspx
/api/v1/token
/api/v1/folders
/api/v1/folders/{id}/files?uploadType=resumable
```

---

## Operator-Grade HTTP Headers

```
X-siLock-Transaction
X-siLock-Username
X-siLock-Password
X-siLock-Challenge
X-siLock-SessVar
X-siLock-ErrorCode
X-siLock-ErrorDescription
X-siLock-Comment
X-File-Hash
Content-Range
```

---

## Header Smuggling — The First Bug

The MOVEit `CrackInput` header-sanitization routine accepts request headers that *end* with the expected name. Supplying two headers — one with a one-byte prefix, one clean — bypasses the sanitization while still being read by the downstream code.

```
XX-siLock-Transaction: folder_add_by_path
X-siLock-Transaction: session_setvars
```

This routes the request through `DoTransaction` with the attacker-controlled transaction value, reaching `SetAllSessionVarsFromHeaders()` despite its localhost-only restriction (defeated by routing through the relay).

---

## Critical Functions and Methods

| Symbol | Role |
|---|---|
| `action_m2` | `MOVEitISAPI.dll` entry; parses `action=m2` requests |
| `CrackInput` | Header sanitization routine (bypassed via dual-header trick) |
| `DoTransaction` | Transaction dispatcher in `machine2.aspx` backend |
| `SetAllSessionVarsFromHeaders` | Maps unsanitized `X-siLock-SessVar*` headers to session variables (removed in patch) |
| `LoadFromSession` | Restores session variables in `guestaccess.aspx` |
| `FolderAddByPath` | Folder-creation handler exposed via the transaction dispatcher |
| `MsgPostForGuest` | Guest-message dispatch path; reaches SQL injection sink |
| `UserGetUsersWithEmailAddress` | SQL injection sink — concatenates email substring into query |
| `GetFileUploadInfo` | Reads file `State` column for the resumable-upload deserialization |
| `DeserializeFileUploadStream` | Unsafe `BinaryFormatter` deserialization on attacker-controlled bytes |
| `GrantSessionToken` | OAuth session-token generation; abused via federated-auth chain |

---

## SQL Injection Chain

### Initial Vector
Header smuggling registers `transaction=session_setvars` with arbitrary `X-siLock-SessVar*` payloads. The `SelfProvisionedRecips` value (set via `X-siLock-SessVar0: MyPkgSelfProvisionedRecips: <payload>`) flows into a query without sanitization.

### Injection Point 1 — Guest Access Email Lookup
```sql
SELECT Username, Permission, LoginName, Email FROM users
WHERE InstID=0 AND Deleted=0 AND Permission>=10
AND (Email='[INJECTION]' OR ...)
```

### Injection Point 2 — Access Code Lookup
```sql
UPDATE guestfileaccess SET Viewed=1 WHERE AccessCode='[PAYLOAD]'
```

### Privilege Escalation — Insert Active Session
```sql
INSERT INTO activesessions (SessionID, Username, LoginName, LastTouch,
  InterfaceCode, IPAddress) VALUES (...)
```

This grants the attacker a usable session bound to a privileged account.

---

## Unsanitized Session Variables

Settable via `X-siLock-SessVar*` headers; not cleaned by `XHTMLClean`:

- `MyUsername`
- `MyPkgValidationCode`
- `MyInstMessaging`
- `MyGuestEmailAddr`
- `MyPkgID`
- `MyPkgSelfProvisionedRecips`
- `MyPkgAccessCode`
- `MyPkgInstID`

---

## RCE Path — BinaryFormatter Deserialization

1. Craft `ysoserial.net` `WindowsIdentity` gadget chain
2. Submit it as the `comments` field on a new resumable upload
3. Use SQL injection to copy the `comments` value into the `fileuploadinfo.state` column
4. Trigger `DeserializeFileUploadStream` by resuming the upload — `BinaryFormatter.Deserialize` runs the gadget chain

### The Vulnerable Method
```csharp
private FileTransferStream DeserializeFileUploadStream(DataFilePath filePath)
{
    if (this._uploadState.Length == 0)
    {
        return this.CreateFileUploadStream(filePath);
    }
    BinaryFormatter binaryFormatter = new BinaryFormatter
    {
        Context = new StreamingContext(StreamingContextStates.All, fileHeaderStream)
    };
    using (MemoryStream memoryStream = new MemoryStream(this._uploadState))
    {
        fileTransferStream = (FileTransferStream)binaryFormatter.Deserialize(memoryStream);
    }
    return fileTransferStream;
}
```

---

## Patch Notes

The patch removes `SetAllSessionVarsFromHeaders` — the original sin that lets unauthenticated callers control session state. Without this method, the session-variable poisoning route into `UserGetUsersWithEmailAddress` is closed off.

---

## Detection

POST requests to `/guestaccess.aspx` carrying `X-siLock-SessVar*` headers with SQL metacharacters or binary-serialization signatures are the highest-fidelity indicator. Resume-upload requests immediately after suspicious `/guestaccess.aspx` traffic are the deserialization-trigger signal.

---

## Attribution

Microsoft and Mandiant both attribute exploitation to the Cl0p ransomware group, the same actor behind the GoAnywhere MFT, Accellion FTA, and SolarWinds Serv-U zero-day campaigns. Mandiant tracks the post-exploitation toolkit, including the LEMURLOOT web shell deployed to `human2.aspx`, under the FIN11 cluster.
