# CVE-2021-3560 - Red Hat Bugzilla Advisory

**Source URL:** https://bugzilla.redhat.com/show_bug.cgi?id=1961710
**CVE:** CVE-2021-3560
**Fetched:** 2026-05-18
**Source type:** vendor_advisory

---

## Vulnerability Summary

CVE-2021-3560 is a local privilege escalation flaw in polkit affecting the `polkit_system_bus_name_get_creds_sync()` function. The vulnerability allows unprivileged local users to execute polkit-protected actions with root privileges.

## Technical Details

**Root Cause:**
The vulnerability occurs when a requesting process disconnects from dbus-daemon immediately before `polkit_system_bus_name_get_creds_sync()` executes. The function receives an error from dbus-daemon but incorrectly returns TRUE instead of FALSE, signaling success despite the failure.

**Impact Chain:**
Callers failing to check error conditions assume uid=0 (root ownership) because the `AsyncGetBusNameCredsData` struct initializes to zero. This misidentification grants unauthorized root-level access to protected D-Bus methods.

**Attack Surface:**
Any local attacker could leverage vulnerable calltraces to:
- Install packages
- Create administrator accounts
- Execute other privileged operations depending on available D-Bus destinations

## Affected Component

**Package:** polkit
**Fixed Version:** polkit 0.119

## Resolution

Red Hat addressed this across multiple products:
- Red Hat Enterprise Linux 8.x variants (via RHSA-2021:2236, RHSA-2021:2237, RHSA-2021:2238)
- Red Hat Virtualization 4 (via RHSA-2021:2522)
- Red Hat OpenShift Container Platform 4.7 (via RHSA-2021:2555)

**Upstream Fix:** Available at freedesktop.org polkit repository commit a04d13affe0fa53ff618e07aa8f57f4c0e3b9b81
