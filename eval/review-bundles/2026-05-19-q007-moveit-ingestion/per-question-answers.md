# Per-question answer extracts

Raw Hermes answer text and score numbers for engineer review. No correctness claims; the rubric numbers are deterministic substring matches and do not assess technical accuracy.

## q-001

**Category:** cve-specific
**Question:** Spring4Shell — what's the actual CVE-2022-22965 primitive on a Spring MVC app, and why does it require a non-default deployment to hit?

**Score breakdown:**

- combined: 0.925
- retrieval_score: 0.925
- path_recall: 1.000
- substring_recall: 0.750
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `spring4shell/blog_jfrog-spring4shell`  (rerank=1.000)
2. `spring4shell/blog_jfrog-spring4shell`  (rerank=0.999)
3. `spring4shell/blog_jfrog-spring4shell`  (rerank=0.998)
4. `spring4shell/blog_jfrog-spring4shell`  (rerank=0.997)
5. `spring4shell/blog_jfrog-spring4shell`  (rerank=0.995)

**Hermes answer text:**

```
(empty)
```

## q-003

**Category:** cve-specific
**Question:** Walk me through PwnKit (CVE-2021-4034) — what's the bug in pkexec, what's the trigger, and what's the minimal exploit payload structure?

**Score breakdown:**

- combined: 1.000
- retrieval_score: 1.000
- path_recall: 1.000
- substring_recall: 1.000
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `pwnkit/exploit_db`  (rerank=1.000)
2. `pwnkit/nvd`  (rerank=1.000)
3. `pwnkit/nvd`  (rerank=0.999)
4. `pwnkit/blog_qualys-pwnkit`  (rerank=0.999)
5. `pwnkit/blog_qualys-pwnkit`  (rerank=0.996)

**Hermes answer text:**

```
(empty)
```

## q-004

**Category:** cve-specific
**Question:** Explain Baron Samedit (CVE-2021-3156) — what triggers the heap overflow in sudo, what's the heap layout abuse, what's affected?

**Score breakdown:**

- combined: 1.000
- retrieval_score: 1.000
- path_recall: 1.000
- substring_recall: 1.000
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `sudo-baron-samedit/exploit_db`  (rerank=0.999)
2. `sudo-baron-samedit/blog_qualys-baron-samedit`  (rerank=0.998)
3. `sudo-baron-samedit/blog_qualys-baron-samedit`  (rerank=0.996)
4. `sudo-baron-samedit/blog_qualys-baron-samedit`  (rerank=0.993)
5. `sudo-baron-samedit/vendor_advisory`  (rerank=0.987)

**Hermes answer text:**

```
(empty)
```

## q-005

**Category:** cve-specific
**Question:** ProxyShell — describe the three CVEs that compose the Exchange chain, and walk through the on-prem exploitation flow end-to-end.

**Score breakdown:**

- combined: 0.925
- retrieval_score: 0.925
- path_recall: 1.000
- substring_recall: 0.750
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `proxylogon/exploit_db`  (rerank=0.996)
2. `proxyshell-exchange/nvd_34473`  (rerank=0.993)
3. `proxyshell-exchange/blog_zdi_proxyshell`  (rerank=0.993)
4. `proxyshell-exchange/nvd_34523`  (rerank=0.992)
5. `proxyshell-exchange/blog_zdi_proxyshell`  (rerank=0.991)

**Hermes answer text:**

```
(empty)
```

## q-006

**Category:** cve-specific
**Question:** CitrixBleed (CVE-2023-4966) — what's the leak primitive on NetScaler ADC/Gateway and how do I both verify and exploit it?

**Score breakdown:**

- combined: 1.000
- retrieval_score: 1.000
- path_recall: 1.000
- substring_recall: 1.000
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `citrixbleed-netscaler/blog_assetnote`  (rerank=0.997)
2. `citrixbleed-netscaler/blog_bleepingcomputer`  (rerank=0.991)
3. `CVE Exploits/README.md`  (rerank=0.985)
4. `citrixbleed-netscaler/blog_bleepingcomputer`  (rerank=0.979)
5. `citrixbleed-netscaler/blog_assetnote`  (rerank=0.965)

**Hermes answer text:**

```
(empty)
```

## q-007

**Category:** cve-specific
**Question:** MOVEit Transfer CVE-2023-34362 — what's the SQLi-to-RCE chain Cl0p used?

**Score breakdown:**

- combined: 0.850
- retrieval_score: 0.850
- path_recall: 1.000
- substring_recall: 0.500
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `moveit/blog_assetnote`  (rerank=1.000)
2. `moveit/blog_horizon3_deepdive`  (rerank=1.000)
3. `moveit/nvd`  (rerank=0.999)
4. `moveit/blog_horizon3`  (rerank=0.999)
5. `moveit/blog_horizon3_deepdive`  (rerank=0.999)

**Hermes answer text:**

```
(empty)
```

## q-008

**Category:** cve-specific
**Question:** Distinguish Confluence CVE-2022-26134 (OGNL injection) from CVE-2023-22515 (broken access control) — different primitives, different mitigations.

**Score breakdown:**

- combined: 1.000
- retrieval_score: 1.000
- path_recall: 1.000
- substring_recall: 1.000
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `confluence/blog_rapid7`  (rerank=0.999)
2. `confluence/nvd`  (rerank=0.998)
3. `confluence/vendor_advisory`  (rerank=0.988)
4. `confluence/blog_rapid7`  (rerank=0.975)
5. `confluence-privesc/nvd`  (rerank=0.971)

**Hermes answer text:**

```
(empty)
```

## q-009

**Category:** cve-specific
**Question:** polkit CVE-2021-3560 — what's the authentication bypass, what's the dbus-send trigger, and which distributions backported the fix late?

**Score breakdown:**

- combined: 0.925
- retrieval_score: 0.925
- path_recall: 1.000
- substring_recall: 0.750
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `polkit-dbus/blog_github_security`  (rerank=0.999)
2. `polkit-dbus/blog_github_security`  (rerank=0.999)
3. `polkit-dbus/nvd`  (rerank=0.997)
4. `polkit-dbus/blog_github_security`  (rerank=0.992)
5. `polkit-dbus/vendor_advisory`  (rerank=0.982)

**Hermes answer text:**

```
(empty)
```

## q-010

**Category:** cve-specific
**Question:** GoAnywhere MFT CVE-2023-0669 — what's the pre-auth RCE primitive and which path/endpoint is the entry point?

**Score breakdown:**

- combined: 0.925
- retrieval_score: 0.925
- path_recall: 1.000
- substring_recall: 0.750
- fact_score: n/a
- hallucination_penalty: n/a

**Retrieved chunks (top-5):**

1. `goanywhere-mft/blog_nuclei`  (rerank=1.000)
2. `goanywhere-mft/nvd`  (rerank=0.998)
3. `src/pentesting-web/deserialization/java-signedobject-gated-deserialization.md`  (rerank=0.994)
4. `src/pentesting-web/deserialization/java-signedobject-gated-deserialization.md`  (rerank=0.981)
5. `moveit/blog_horizon3_deepdive`  (rerank=0.927)

**Hermes answer text:**

```
(empty)
```
