# The Dirty Pipe Vulnerability — cm4all.com writeup (CVE-2022-0847)

**Source URL:** https://dirtypipe.cm4all.com/
**CVE:** CVE-2022-0847
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

This vulnerability affects Linux kernels 5.8 through 5.16.10 (and related stable branches), allowing unprivileged processes to overwrite data in read-only files through page cache corruption.

## Discovery Context

The vulnerability was identified during investigation of corrupted gzip log files on CM4all's hosting infrastructure. Access logs were showing incorrect CRC32 checksums and file length values, consistently containing ZIP header signatures ("PK" bytes: `50 4b 01 02 1e 03 14 00`) at corruption points—data that should never have been written to those files.

## Root Cause Analysis

### The Bug Chain

The vulnerability stems from uninitialized flags in pipe buffer structures. Specifically:

- **Commit 241699cd72a8 (Linux 4.9, 2016)**: Functions allocating `struct pipe_buffer` instances failed to initialize the `flags` member
- **Commit f6dd975583bd (Linux 5.8, 2020)**: Refactored pipe buffer operations to use per-buffer `PIPE_BUF_FLAG_CAN_MERGE` flag instead of pointer comparisons

The second commit made the pre-existing bug exploitable. When page cache pages gained uninitialized flags, they could inherit the `CAN_MERGE` flag, allowing subsequent writes to modify cached file data.

## Technical Mechanism

### Pipe Buffer Architecture

Linux implements pipes as rings of `struct pipe_buffer` entries, each referencing a memory page (typically 4 KB). Two categories exist:

1. **Anonymous buffers**: Created by direct writes, mergeable with subsequent writes
2. **Page cache buffers**: Created via `splice()` from files, normally non-mergeable

The vulnerability occurs because page cache buffers created through specific code paths retain uninitialized `PIPE_BUF_FLAG_CAN_MERGE` flags from prior ring entries.

### Attack Sequence

The exploit requires:

1. Create pipe; fill completely with arbitrary data to set `PIPE_BUF_FLAG_CAN_MERGE` in all ring slots
2. Drain pipe completely—flags remain set but buffers are freed
3. Open target file with read-only permissions
4. Use `splice()` to load one byte from target file into pipe (offset must not be page-aligned)
5. Write arbitrary data to pipe—data overwrites page cache instead of creating new buffer

## Exploitation Constraints

- Attacker needs read permissions on target file
- Target offset cannot begin at page boundary (need ≥1 byte of prior page data)
- Write cannot cross page boundary
- File size cannot be increased

Despite these constraints, the vulnerability enables writing to:
- Immutable files
- Read-only `btrfs` snapshots
- Files on read-only mounts (including CD-ROMs)

Page cache modifications don't automatically "dirty" pages, allowing changes to persist only while cached or until kernel reclaim.

## Proof-of-Concept Exploit

The provided C program demonstrates overwriting file contents. Key operations:

```c
prepare_pipe(int p[2])  // Fill and drain to set CAN_MERGE flags
splice(fd, &offset, p[1], NULL, 1, 0)  // Load one cached byte
write(p[1], data, data_size)  // Overwrite cache via merge
```

Limitations explicitly checked: page boundary alignment and cross-page writes.

## Affected Versions and Fixes

**Vulnerable**: Linux 5.8 through 5.16.10, 5.15.24, 5.10.101

**Fixed in**: Linux 5.16.11, 5.15.25, 5.10.102

The patch ensures `flags` initialization in affected code paths, setting them to zero (non-mergeable for page cache buffers).

## Timeline

- **Feb 19, 2022**: Vulnerability identified
- **Feb 20-21**: Patch and exploit sent to kernel security team; reproduced on Google Pixel 6
- **Feb 23**: Stable kernel releases with fix
- **Feb 24**: Android kernel integration
- **Feb 28**: linux-distros mailing list notification
- **Mar 7**: Public disclosure
