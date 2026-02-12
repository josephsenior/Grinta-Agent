from typing import Any
import ast
import logging
from backend.events.action import Action, ActionSecurityRisk, FileWriteAction, CmdRunAction

logger = logging.getLogger(__name__)

class SecurityAnalyzer:
    """Analyzes actions for security risks using structural analysis."""
    
    async def security_risk(self, action: Action) -> ActionSecurityRisk:
        """Evaluate the security risk of an action.
        
        Uses AST analysis for Python file edits to ensure syntax validity.
        Checks shell commands for dangerous patterns.
        """
        
        if isinstance(action, FileWriteAction):
            # Check Python files for syntax errors
            if action.path.endswith('.py'):
                try:
                    ast.parse(action.content)
                except SyntaxError:
                    logger.warning(f"Security check failed: Syntax error in {action.path}")
                    return ActionSecurityRisk.HIGH
                except Exception as e:
                    logger.warning(f"Security check warning: Could not parse {action.path}: {e}")
                    return ActionSecurityRisk.MEDIUM
                    
        elif isinstance(action, CmdRunAction):
            # Basic heuristic for dangerous commands
            cmd = action.command.lower()
            if "rm -rf" in cmd or "remove-item" in cmd and "-force" in cmd:
                return ActionSecurityRisk.HIGH
                
        return ActionSecurityRisk.LOW
