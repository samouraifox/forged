# CVE-2016-3134 - Red Hat Security Advisory RHSA-2016:1847

**Source URL:** https://access.redhat.com/errata/RHSA-2016:1847
**CVE:** CVE-2016-3134
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

## Advisory Details

**Title:** RHSA-2016:1847 - Security Advisory
**Type:** Important
**Issued:** 2016-09-14

## CVE-2016-3134 (Important)

A bounds-checking flaw was identified in the Linux kernel's netfilter implementation. The vulnerability exists in the `mark_source_chains()` function within "net/ipv4/netfilter/ip_tables.c". The issue allows user-supplied `ipt_entry` structures with large "next_offset" fields to write to counter values at supplied offsets without proper validation.

## Additional CVEs in This Advisory

**CVE-2016-4997 (Important):** A flaw affecting 32-bit process handling on 64-bit systems permits attackers to alter arbitrary kernel memory when unloading kernel modules. While typically restricted to root users, this can be exploited in privileged container environments with CONFIG_USER_NS and CONFIG_NET_NS enabled.

**CVE-2016-4998 (Moderate):** An out-of-bounds heap memory access vulnerability in `setsockopt()` causes denial of service, heap disclosure, or further impact. Though normally root-restricted, processes with `cap_sys_admin` in privileged containers may trigger this flaw.

## Affected Products

The update applies to Red Hat Enterprise Linux 7 across multiple variants including Server, Workstation, Desktop, and specialized editions for IBM z Systems and Power architectures.

## Key Updates

The kernel version **3.10.0-327.36.1.el7** addresses these security issues alongside bug fixes for IPMI race conditions, I/O driver stability, and SCTP SELinux label inheritance.
