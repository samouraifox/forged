# Citrix Bleed: Leaking Session Tokens with CVE-2023-4966 (Assetnote)

**Source URL:** https://www.assetnote.io/resources/research/citrix-bleed-leaking-session-tokens-with-cve-2023-4966
**CVE:** CVE-2023-4966
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

Assetnote researchers discovered CVE-2023-4966, a critical information disclosure flaw in Citrix NetScaler ADC and Gateway with a CVSS score of 9.4. The vulnerability leaks valid session tokens through memory disclosure.

## Technical Root Cause

The flaw stems from misuse of `snprintf()` in the OpenID Connect Discovery endpoint handlers. While `snprintf()` prevents buffer overflow, the developers incorrectly assumed it returns bytes *written*. Actually, it returns bytes that *would have* been written if space existed.

**Vulnerable code pattern:**
```c
iVar3 = snprintf(print_temp_rule, 0x20000,
    "{\"issuer\": \"https://%.*s\", ...}",
    uVar5, pbVar8, uVar5, pbVar8, uVar5, pbVar8, ...);
ns_vpn_send_response(param_1, 0x100040, print_temp_rule, iVar3);
```

When the formatted output exceeds 0x20000 bytes, `snprintf()` returns the overflow size, but the buffer still contains only 0x20000 bytes. The function then transmits memory beyond the intended buffer.

## Exploitation Method

**Affected endpoints (unauthenticated access):**
- `/oauth/idp/.well-known/openid-configuration`
- `/oauth/rp/.well-known/openid-configuration`

The hostname parameter appears eight times in the JSON response. Attackers craft a request with an extremely long `Host` header to trigger buffer overflow:

```
GET /oauth/idp/.well-known/openid-configuration HTTP/1.1
Host: a <repeated 24812 times>
```

This generates a response with leaked memory containing valid session tokens (65-byte hex strings).

## Token Validation

Researchers verified extracted tokens work as valid `NSC_AAAC` session cookies, enabling authenticated access without credentials.

## Affected Versions

- NetScaler ADC/Gateway 13.1-48.47 (vulnerable)
- NetScaler ADC/Gateway 13.1-49.15 (patched)

## Mitigation

Apply Citrix security patches immediately. The patch adds bounds checking before response transmission.

## Research Credit

Original write-up by Dylan Pindur, Assetnote.
