"""Enhanced command risk analysis for autonomous agent safety.

This module provides multi-layer command analysis to detect dangerous operations
including encoded commands, privilege escalation, and container escapes.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from enum import Enum

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    ActionSecurityRisk,
    CmdRunAction,
    IPythonRunCellAction,
)


class RiskCategory(str, Enum):
    """Categories of command risks."""

    CRITICAL = "critical"  # System destruction, data loss
    HIGH = "high"  # Privilege escalation, container escape
    MEDIUM = "medium"  # Network operations, file modifications
    LOW = "low"  # Safe operations


@dataclass
class CommandRiskAssessment:
    """Result of command risk analysis."""

    risk_level: ActionSecurityRisk
    risk_category: RiskCategory
    reason: str
    matched_patterns: list[str]
    is_encoded: bool = False
    is_network_operation: bool = False
    affects_system: bool = False


class CommandAnalyzer:
    """Multi-layer command security analyzer.

    Analyzes commands through multiple detection layers:
    1. Pattern matching for known dangerous commands
    2. Encoding detection (base64, hex, eval)
    3. Network operation detection
    4. File system impact analysis
    5. Container/system modification detection
    """

    # Critical commands that destroy data or system
    CRITICAL_PATTERNS = [
        r"\brm\s+-rf\s+/",  # Delete root
        r"\brm\s+-rf\s+\*",  # Delete all files
        r"\bdd\s+if=",  # Disk operations
        r":\(\)\{\s*:\|:\&\s*\};:",  # Fork bomb
        r"\bmkfs\.",  # Format filesystem
        r"\bfdisk\b",  # Partition operations
        r">\s*/dev/sd",  # Write to disk
        r"\bshred\b",  # Secure delete
        r"\bkill\s+-9\s+1\b",  # Kill init process
    ]

    # High-risk patterns: privilege escalation, container escape
    HIGH_RISK_PATTERNS = [
        r"\bchmod\s+.*\+s\b",  # SUID bit
        r"\bchmod\s+.*777",  # World writable
        r"\bchown\s+-R",  # Recursive ownership change
        r"\bsudo\s+.*rm",  # Sudo with rm
        r"\bsudo\s+.*dd",  # Sudo with dd
        r"--privileged",  # Docker privileged mode
        r"\bdocker\s+run.*--privileged",
        r"/etc/passwd",  # Password file access
        r"/etc/shadow",  # Shadow file access
        r"\breboot\b",  # System reboot
        r"\bshutdown\b",  # System shutdown
        r"\binit\s+[0-6]",  # Change runlevel
        r"\bsystemctl\s+(stop|disable|mask)",  # Disable services
    ]

    # High-risk patterns should include network operations piped to shell (moved from MEDIUM)
    # Medium-risk patterns: other network operations
    MEDIUM_RISK_PATTERNS = [
        r"\beval\s*\$",  # Eval with variable
        r"\bsource\s+<\(",  # Process substitution
    ]

    # Network shell execution patterns (HIGH RISK - moved from MEDIUM)
    NETWORK_SHELL_PATTERNS = [
        r"\bcurl\s+.*\|\s*bash",  # Curl pipe to bash
        r"\bcurl\s+.*\|\s*sh",  # Curl pipe to sh
        r"\bwget\s+.*\|\s*bash",  # Wget pipe to bash
        r"\bwget\s+.*\|\s*sh",  # Wget pipe to sh
        r"\bcurl\s+.*sudo",  # Curl with sudo
        r"\bwget\s+.*sudo",  # Wget with sudo
    ]

    # Encoding detection patterns
    ENCODING_PATTERNS = [
        r"\bbase64\s+(-d|--decode)",  # Base64 decode
        r"\bxxd\s+-r",  # Hex decode
        r"\beval\s*\$\(",  # Eval with command substitution
        r"\$\(echo\s+.*\|",  # Echo pipe (often used for encoding)
        r"\\x[0-9a-fA-F]{2}",  # Hex escape sequences
    ]

    def __init__(self, config: dict | None = None) -> None:
        """Initialize the command analyzer.

        Args:
            config: Optional configuration dictionary with:
                - blocked_patterns: Additional regex patterns to block
                - allowed_exceptions: Commands to whitelist
                - risk_threshold: Minimum risk level to flag
        """
        self.config = config or {}
        self.custom_blocked_patterns = self.config.get("blocked_patterns", [])
        self.allowed_exceptions = self.config.get("allowed_exceptions", [])
        self.risk_threshold = self.config.get("risk_threshold", "high")

    def analyze_action(self, action: Action) -> CommandRiskAssessment:
        """Analyze an action for security risks.

        Args:
            action: The action to analyze

        Returns:
            CommandRiskAssessment with risk level and details
        """
        if isinstance(action, CmdRunAction):
            return self.analyze_command(action.command)
        if isinstance(action, IPythonRunCellAction):
            return self.analyze_python_code(action.code)
        # Non-executable actions are low risk
        return CommandRiskAssessment(
            risk_level=ActionSecurityRisk.LOW,
            risk_category=RiskCategory.LOW,
            reason="Non-executable action",
            matched_patterns=[],
        )

    def analyze_command(self, command: str) -> CommandRiskAssessment:
        """Analyze a shell command for security risks.

        Args:
            command: The shell command to analyze

        Returns:
            CommandRiskAssessment with detailed risk information
        """
        # Check if command is whitelisted
        if self._is_whitelisted(command):
            return CommandRiskAssessment(
                risk_level=ActionSecurityRisk.LOW,
                risk_category=RiskCategory.LOW,
                reason="Whitelisted command",
                matched_patterns=[],
            )

        matched_patterns = []

        # Check critical patterns (Layer 1)
        if assessment := self._check_critical_patterns(command, matched_patterns):
            return assessment

        # Check encoding (Layer 2)
        if assessment := self._check_encoding_patterns(command, matched_patterns):
            return assessment

        # Check network shell patterns (Layer 3)
        if assessment := self._check_network_shell_patterns(command, matched_patterns):
            return assessment

        # Check high-risk patterns (Layer 4)
        if assessment := self._check_high_risk_patterns(command, matched_patterns):
            return assessment

        # Check medium-risk patterns (Layer 5)
        return self._check_medium_low_risk_patterns(command, matched_patterns)

    def _check_critical_patterns(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment | None:
        """Check for critical security patterns.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment if critical pattern found, None otherwise
        """
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                matched_patterns.append(pattern)
                logger.warning(f"CRITICAL command detected: {command[:100]}")
                return CommandRiskAssessment(
                    risk_level=ActionSecurityRisk.HIGH,
                    risk_category=RiskCategory.CRITICAL,
                    reason=f"Critical system operation detected: {pattern}",
                    matched_patterns=matched_patterns,
                    affects_system=True,
                )
        return None

    def _check_encoding_patterns(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment | None:
        """Check for encoded/obfuscated commands.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment if encoding detected, None otherwise
        """
        if self._check_encoding(command):
            matched_patterns.append("encoded_command")
            logger.warning(f"Encoded command detected: {command[:100]}")
            return CommandRiskAssessment(
                risk_level=ActionSecurityRisk.HIGH,
                risk_category=RiskCategory.HIGH,
                reason="Potentially obfuscated command detected",
                matched_patterns=matched_patterns,
                is_encoded=True,
            )
        return None

    def _check_network_shell_patterns(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment | None:
        """Check for network shell execution patterns.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment if network shell pattern found, None otherwise
        """
        for pattern in self.NETWORK_SHELL_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                matched_patterns.append(pattern)
                logger.warning(f"HIGH RISK network shell command detected: {command[:100]}")
                return CommandRiskAssessment(
                    risk_level=ActionSecurityRisk.HIGH,
                    risk_category=RiskCategory.HIGH,
                    reason=f"Network shell execution detected: {pattern}",
                    matched_patterns=matched_patterns,
                    is_network_operation=True,
                )
        return None

    def _check_high_risk_patterns(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment | None:
        """Check for high-risk patterns.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment if high-risk pattern found, None otherwise
        """
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                matched_patterns.append(pattern)
                logger.warning(f"HIGH RISK command detected: {command[:100]}")
                return CommandRiskAssessment(
                    risk_level=ActionSecurityRisk.HIGH,
                    risk_category=RiskCategory.HIGH,
                    reason=f"High-risk operation detected: {pattern}",
                    matched_patterns=matched_patterns,
                    affects_system=True,
                )
        return None

    def _check_medium_low_risk_patterns(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment:
        """Check for medium and low-risk patterns.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment with appropriate risk level
        """
        command_lower = command.lower()
        is_network_op = False

        for pattern in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                matched_patterns.append(pattern)
                is_network_op = "curl" in command_lower or "wget" in command_lower

        # Check custom blocked patterns
        if assessment := self._check_custom_blocked(command, matched_patterns):
            return assessment

        # Return final assessment
        if matched_patterns:
            logger.info(f"Medium risk command: {command[:100]}")
            return CommandRiskAssessment(
                risk_level=ActionSecurityRisk.MEDIUM,
                risk_category=RiskCategory.MEDIUM,
                reason="Medium-risk patterns detected",
                matched_patterns=matched_patterns,
                is_network_operation=is_network_op,
            )

        return CommandRiskAssessment(
            risk_level=ActionSecurityRisk.LOW,
            risk_category=RiskCategory.LOW,
            reason="No risk patterns detected",
            matched_patterns=[],
        )

    def _check_custom_blocked(self, command: str, matched_patterns: list[str]) -> CommandRiskAssessment | None:
        """Check for custom blocked patterns.

        Args:
            command: Command to analyze
            matched_patterns: List to append matched patterns to

        Returns:
            CommandRiskAssessment if custom pattern matched, None otherwise
        """
        for pattern in self.custom_blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                matched_patterns.append(pattern)
                return CommandRiskAssessment(
                    risk_level=ActionSecurityRisk.HIGH,
                    risk_category=RiskCategory.HIGH,
                    reason=f"Custom blocked pattern matched: {pattern}",
                    matched_patterns=matched_patterns,
                )
        return None

    def analyze_python_code(self, code: str) -> CommandRiskAssessment:
        """Analyze Python code for security risks.

        Args:
            code: The Python code to analyze

        Returns:
            CommandRiskAssessment with risk information
        """
        matched_patterns = []
        code.lower()

        # Check for dangerous Python operations
        dangerous_patterns = [
            (r"\bexec\s*\(", "exec() function call"),
            (r"\beval\s*\(", "eval() function call"),
            (r"\b__import__\s*\(", "__import__ function call"),
            (r"os\.system\s*\(", "os.system() call"),
            (r"subprocess\..*shell\s*=\s*True", "subprocess with shell=True"),
            (r'open\s*\([^)]*,\s*[\'"]w', "file write operation"),
            (r"\brm\s+-rf", "rm -rf in subprocess"),
        ]

        for pattern, description in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                matched_patterns.append(description)

        if matched_patterns:
            logger.info(f"Python code with risk patterns: {matched_patterns}")
            return CommandRiskAssessment(
                risk_level=ActionSecurityRisk.MEDIUM,
                risk_category=RiskCategory.MEDIUM,
                reason=f"Potentially risky Python operations: {', '.join(matched_patterns)}",
                matched_patterns=matched_patterns,
            )

        return CommandRiskAssessment(
            risk_level=ActionSecurityRisk.LOW,
            risk_category=RiskCategory.LOW,
            reason="No risk patterns detected in Python code",
            matched_patterns=[],
        )

    def _check_encoding(self, command: str) -> bool:
        """Check if command uses encoding/obfuscation.

        Args:
            command: Command to check

        Returns:
            True if encoding detected
        """
        for pattern in self.ENCODING_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        # Check for base64-encoded strings
        try:
            # Look for base64-like strings (at least 20 chars, alphanumeric+/+=)
            base64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
            potential_base64 = re.findall(base64_pattern, command)

            for encoded in potential_base64:
                try:
                    decoded = base64.b64decode(encoded, validate=True)
                    # If it decodes and contains shell metacharacters, it's suspicious
                    if any(char in decoded.decode("utf-8", errors="ignore") for char in ["|", "&", ";", "$", "`"]):
                        logger.warning("Suspicious base64 string detected in command")
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        return False

    def _is_whitelisted(self, command: str) -> bool:
        """Check if command is in the whitelist.

        Args:
            command: Command to check

        Returns:
            True if whitelisted
        """
        return any(allowed in command for allowed in self.allowed_exceptions)
