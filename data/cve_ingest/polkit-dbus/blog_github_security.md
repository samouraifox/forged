# CVE-2021-3560 - GitHub Security Lab: Privilege Escalation via polkit

**Source URL:** https://github.blog/2021-06-10-privilege-escalation-polkit-root-on-linux-with-bug/
**CVE:** CVE-2021-3560
**Fetched:** 2026-05-18
**Source type:** blog

---

## Overview

CVE-2021-3560 is a seven-year-old privilege escalation bug in polkit, the Linux authorization system. It "enables an unprivileged local user to get a root shell on the system."

## Vulnerability Timeline

- **Introduced**: 2014 in commit bfa5036, shipped with polkit version 0.113
- **Disclosed**: June 3, 2021
- **Affected**: RHEL 8+, Fedora 21+, Ubuntu 20.04, and Debian testing ("bullseye")
- **Not affected**: RHEL 7, Fedora 20 and earlier, Debian 10 ("buster"), Ubuntu 18.04

## Technical Root Cause

The vulnerability occurs when polkit asks the D-Bus daemon for a requesting process's UID. If the D-Bus connection no longer exists when queried, polkit mishandles the error by treating the disconnected request as originating from UID 0 (root), thereby authorizing it immediately.

The bug resides in the `polkit_system_bus_name_get_creds_sync()` function, which returns `TRUE` even when errors occur. The vulnerable codepath in `check_authorization_sync()` at line 1121 fails to check the error parameter, allowing authorization to proceed: "special case: uid 0, root, is _always_ authorized for anything."

## Timing/Race Condition Mechanics

The exploit requires killing a D-Bus request at precisely the right moment — approximately halfway through processing. This timing is non-deterministic because polkit queries the UID through multiple codepaths; most handle errors correctly, but one does not. This non-determinism likely prevented earlier discovery, as immediate disconnection attempts would follow correct error-handling paths.

## Proof-of-Concept Attack Steps

The attack creates a new privileged user account by:

1. Sending a D-Bus `CreateUser` method call via `dbus-send`
2. Killing the process after ~8 milliseconds (timing varies by system)
3. Repeating until polkit incorrectly authorizes the request
4. Creating a password hash with `openssl passwd -5`
5. Using the same technique to call `SetPassword` method
6. Logging in as the new user and escalating to root via `sudo`

The PoC depends on `accountsservice` and `gnome-control-center` (or similar) being installed due to polkit's `policykit.imply` annotations, which implicitly authorize related actions.

## Fix

The developers resolved this by modifying `polkit_system_bus_name_get_creds_sync()` to return `FALSE` on error, ensuring callers properly validate error conditions before proceeding.
