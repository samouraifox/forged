# CVE-2021-3156 — Baron Samedit — Red Hat Security Advisory RHSA-2021:0221

**Source URL:** https://access.redhat.com/errata/RHSA-2021:0221
**CVE:** CVE-2021-3156
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

Note: sudo.ws/alerts/unescape_reasonable.html returned HTTP 403. RHSA-2021:0221 is cited in NVD references for CVE-2021-3156 and serves as the vendor advisory for Red Hat platforms.

---

## Vulnerability Description

"Heap buffer overflow in argument parsing" vulnerability affecting the sudo utility. This flaw allows attackers to exploit memory management weaknesses in how sudo processes command-line arguments.

## Affected Packages

Updated packages are available across multiple Red Hat Enterprise Linux 7 variants:
- Server (x86_64)
- Workstation (x86_64)
- Desktop (x86_64)
- IBM z Systems (s390x)
- Power big endian (ppc64)
- Power little endian (ppc64le)
- Scientific Computing (x86_64)

The patched version is **sudo-1.8.23-10.el7_9.1** across all architectures.

## Security Classification

Red Hat rated this update as "Important" severity.

## Advisory Details

- **Advisory ID:** RHSA-2021:0221
- **Issued:** January 26, 2021
- **Bug ID:** BZ#1917684
- **Security bulletin:** RHSB-2021-002
- **Application guidance:** https://access.redhat.com/articles/11258

The advisory lists SHA-256 checksums for all package variants to verify download integrity.
