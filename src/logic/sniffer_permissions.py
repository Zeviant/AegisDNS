"""OS-aware handling for the packet sniffer's raw-socket permission failures.

The sniffer code itself (sniffer_test/packet_sniffer.py) is not OS-specific —
Scapy's sniff() works the same way on every platform. What differs is that
Linux denies raw-socket access to unprivileged processes by default, while
this app's tested Windows setups already had that access (Npcap configured
for non-admin capture, or the app run elevated). This module supplies the
Linux-specific fix path without touching the Windows/macOS behavior at all.
"""

import platform
import subprocess
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def build_permission_message(raw_error: str) -> tuple[str, bool]:
    """Returns (user-facing message, whether a one-click auto-fix is offered)."""
    system = platform.system()

    if system == "Windows":
        return (
            "Packet capture failed to start.\n\n"
            "On Windows this almost always means Npcap isn't installed (or "
            "was installed with capture restricted to Administrators). Install "
            "or repair Npcap from npcap.com and try again.\n\n"
            f"Details: {raw_error}"
        ), False

    if system == "Darwin":
        return (
            "Packet capture failed to start.\n\n"
            "On macOS, raw packet capture requires elevated privileges — quit "
            "AegisDNS and relaunch it with 'sudo'.\n\n"
            f"Details: {raw_error}"
        ), False

    if system == "Linux":
        if is_frozen():
            # Deliberately not offering an automatic setcap fix here: PyInstaller's
            # Linux bootloader locates its bundled shared libraries via
            # LD_LIBRARY_PATH, which the kernel's dynamic loader ignores for
            # binaries that carry file capabilities (the same "secure execution"
            # hardening applied to setuid binaries). Granting cap_net_raw directly
            # on this executable risks breaking it outright. Running the whole
            # app via sudo/pkexec sidesteps that, since it doesn't rely on file
            # capabilities.
            return (
                "Packet capture needs raw-socket permission, which Linux denies "
                "by default.\n\n"
                "Quit AegisDNS and relaunch it as:\n"
                f"    sudo {sys.executable}\n\n"
                "(This packaged build can't be granted that permission "
                "permanently without risking breaking how it loads its "
                "bundled libraries — running it from source instead lets you "
                "grant it once, permanently, via the button below.)\n\n"
                f"Details: {raw_error}"
            ), False
        else:
            return (
                "Packet capture needs raw-socket permission, which Linux denies "
                "by default.\n\n"
                "Click \"Grant permission\" below to allow it once (you'll be "
                "asked for your password), then restart AegisDNS. This is a "
                "one-time setup step.\n\n"
                f"Manual equivalent: sudo setcap cap_net_raw,cap_net_admin=eip {sys.executable}"
            ), True

    return f"Packet capture failed to start: {raw_error}", False


def grant_linux_capture_permission() -> tuple[bool, str]:
    """Grants cap_net_raw/cap_net_admin to the current Python interpreter via
    setcap, using pkexec for the one-time graphical privilege prompt.

    Only meaningful (and only offered by build_permission_message) when NOT
    running from a PyInstaller bundle — see the note above.
    """
    exe = sys.executable
    try:
        result = subprocess.run(
            ["pkexec", "setcap", "cap_net_raw,cap_net_admin=eip", exe],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return False, (
            "pkexec isn't available on this system. Run this manually from a "
            f"terminal instead:\n\nsudo setcap cap_net_raw,cap_net_admin=eip {exe}"
        )
    except subprocess.TimeoutExpired:
        return False, "Timed out waiting for the permission prompt."

    if result.returncode != 0:
        return False, result.stderr.strip() or "setcap failed for an unknown reason."

    return True, "Permission granted. Please restart AegisDNS for it to take effect."
