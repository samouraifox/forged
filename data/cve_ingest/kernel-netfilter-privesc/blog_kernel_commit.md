# CVE-2016-3134 - Linux Kernel Git Commit Fix

**Source URL:** https://github.com/torvalds/linux/commit/54d83fc74aa9ec72794373cb47432c5f7fb1a309
**CVE:** CVE-2016-3134
**Fetched:** 2026-05-18
**Source type:** blog

---

## Commit Metadata

- **Hash**: 54d83fc74aa9ec72794373cb47432c5f7fb1a309
- **Author**: Florian Westphal
- **Committer**: ummakynes
- **Parent**: 6e94e0cfb0887e4013b3b930fa6ab1fe6bb6ba91

## Commit Message Summary

The fix addresses a vulnerability in the `mark_source_chains` function where "a user-supplied ipt_entry structure to have a large next_offset field" could be exploited without proper bounds checking.

**Root Cause**: The `conditional()` function had inconsistent logic across different code paths. While the underflow validator only checked address matching, `mark_source_chains` additionally validated for match presence, creating a discrepancy that allowed invalid rules to be processed.

**Solution**: Unified the unconditional rule detection by modifying the `unconditional()` function to check both:
- `e->target_offset == sizeof(struct ipt_entry)` (no matches present)
- Wildcard address verification via memcmp

## Files Modified

Three netfilter table implementations were patched:
- `net/ipv4/netfilter/arp_tables.c` (9 additions, 9 deletions)
- `net/ipv4/netfilter/ip_tables.c` (11 additions, 12 deletions)
- `net/ipv6/netfilter/ip6_tables.c` (11 additions, 12 deletions)

**Secondary Change**: Error messages were downgraded from `pr_err()` to `pr_debug()` level in underflow validation routines.

## Primary Kernel Reference

Canonical kernel.org URL: http://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/commit/?id=54d83fc74aa9ec72794373cb47432c5f7fb1a309
