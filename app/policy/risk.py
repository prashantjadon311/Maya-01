"""Trusted structural risk classification, independent of model claims."""

from enum import Enum
from pathlib import Path

from app.actions.schema import ActionRequest


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


NEVER_PREAPPROVE_EXECUTABLES = frozenset({
    "sudo", "su", "doas", "pkexec", "env",
    "sh", "bash", "dash", "zsh", "fish",
    "apt", "apt-get", "dpkg", "dnf", "yum", "rpm", "snap", "flatpak",
    "systemctl", "service",
    "rm", "rmdir", "unlink", "shred", "chmod", "chown", "chgrp",
    "dd", "mkfs", "mount", "umount", "shutdown", "reboot", "poweroff",
    "useradd", "userdel", "usermod", "groupadd", "groupdel", "passwd",
    "kill", "pkill", "killall", "iptables", "nft", "ufw",
})


def assess_risk(action: ActionRequest) -> RiskLevel:
    """Classify structure first; an advisory hint can only raise risk."""
    low = {"app.open", "file.read", "file.list", "browser.open", "browser.read"}
    medium = {"file.write", "browser.click", "browser.type", "task.create", "process.run"}
    level = RiskLevel.LOW if action.tool in low else RiskLevel.MEDIUM if action.tool in medium else RiskLevel.HIGH
    if action.tool == "process.run":
        argv = action.arguments.get("argv")
        if not isinstance(argv, list) or not argv or not isinstance(argv[0], str):
            level = RiskLevel.HIGH
        elif Path(argv[0]).name in NEVER_PREAPPROVE_EXECUTABLES:
            level = RiskLevel.HIGH
    levels = list(RiskLevel)
    if action.risk_hint:
        try:
            hint = RiskLevel(action.risk_hint.upper())
        except ValueError:
            return level
        level = levels[max(levels.index(level), levels.index(hint))]
    return level
