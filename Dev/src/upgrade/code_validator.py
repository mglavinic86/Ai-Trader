"""
Code Validator for AI Trader Self-Upgrade System.

Validates generated Python code using AST parsing and security checks.
Ensures code is safe before deployment.

Usage:
    from src.upgrade.code_validator import CodeValidator

    validator = CodeValidator()
    result = validator.validate(code)
    if result.is_valid:
        print("Code is safe to deploy")
"""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Set, Optional, Any

from src.utils.logger import logger


# Whitelist of allowed imports
ALLOWED_IMPORTS = {
    "dataclasses",
    "typing",
    "datetime",
    "math",
    "statistics",
    "collections",
    "functools",
    "re",
    "src",  # Allow src.* imports
}

# Whitelist of allowed from imports (module, name)
ALLOWED_FROM_IMPORTS = {
    ("dataclasses", "dataclass"),
    ("dataclasses", "field"),
    ("typing", "Dict"),
    ("typing", "List"),
    ("typing", "Optional"),
    ("typing", "Any"),
    ("typing", "Tuple"),
    ("typing", "Set"),
    ("datetime", "datetime"),
    ("datetime", "timedelta"),
    ("datetime", "timezone"),
    ("math", "*"),
    ("statistics", "*"),
    ("collections", "defaultdict"),
    ("collections", "Counter"),
    ("functools", "lru_cache"),
    ("src.upgrade.base_filter", "BaseFilter"),
    ("src.upgrade.base_filter", "FilterResult"),
}

# Blacklist of dangerous function calls
DANGEROUS_CALLS = {
    "exec",
    "eval",
    "compile",
    "__import__",
    "open",
    "file",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "getattr",  # Can be dangerous with user input
    "setattr",
    "delattr",
    "hasattr",  # Less dangerous but often used with getattr
}

# Blacklist of dangerous attribute access
DANGEROUS_ATTRIBUTES = {
    "__dict__",
    "__class__",
    "__bases__",
    "__mro__",
    "__subclasses__",
    "__globals__",
    "__code__",
    "__builtins__",
}


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ast_valid: bool = False
    has_base_filter: bool = False
    has_check_method: bool = False
    class_name: Optional[str] = None
    imports_used: Set[str] = field(default_factory=set)


class CodeValidator:
    """
    Validates Python code for safety and correctness.

    Checks:
    1. Syntax validity (AST parsing)
    2. Import whitelist enforcement
    3. Dangerous function call detection
    4. Dangerous attribute access detection
    5. BaseFilter inheritance verification
    6. check() method presence
    """

    def __init__(self):
        self._dangerous_call_pattern = re.compile(
            r'\b(' + '|'.join(DANGEROUS_CALLS) + r')\s*\('
        )

    def validate(self, code: str) -> ValidationResult:
        """
        Validate Python code for safety and correctness.

        Args:
            code: Python source code to validate

        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(is_valid=True)

        # Step 1: Check syntax with AST
        try:
            tree = ast.parse(code)
            result.ast_valid = True
        except SyntaxError as e:
            result.is_valid = False
            result.errors.append(f"Syntax error: {e.msg} at line {e.lineno}")
            return result

        # Step 2: Analyze AST for security issues
        self._analyze_imports(tree, result)
        self._analyze_calls(tree, result)
        self._analyze_attributes(tree, result)

        # Step 3: Verify filter structure
        self._verify_filter_structure(tree, result)

        # Step 4: Additional regex checks for patterns AST might miss
        self._regex_checks(code, result)

        # Final validity check
        if result.errors:
            result.is_valid = False
        elif not result.has_base_filter or not result.has_check_method:
            result.is_valid = False
            if not result.has_base_filter:
                result.errors.append("Class must inherit from BaseFilter")
            if not result.has_check_method:
                result.errors.append("Class must implement check() method")

        return result

    def _analyze_imports(self, tree: ast.AST, result: ValidationResult) -> None:
        """Analyze import statements for security."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    result.imports_used.add(module)

                    if module not in ALLOWED_IMPORTS:
                        result.errors.append(f"Forbidden import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    result.imports_used.add(module)

                    if module not in ALLOWED_IMPORTS:
                        result.errors.append(f"Forbidden import: from {node.module}")

                    # Check specific from imports
                    for alias in node.names:
                        # Allow src.* imports
                        if module == "src":
                            continue

                        # Check if this specific import is allowed
                        allowed = False
                        for allowed_mod, allowed_name in ALLOWED_FROM_IMPORTS:
                            if allowed_mod == node.module or allowed_mod.startswith(module):
                                if allowed_name == "*" or allowed_name == alias.name:
                                    allowed = True
                                    break

                        if not allowed:
                            result.warnings.append(
                                f"Unverified import: from {node.module} import {alias.name}"
                            )

    def _analyze_calls(self, tree: ast.AST, result: ValidationResult) -> None:
        """Analyze function calls for dangerous operations."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check direct function calls
                if isinstance(node.func, ast.Name):
                    if node.func.id in DANGEROUS_CALLS:
                        result.errors.append(f"Dangerous function call: {node.func.id}()")

                # Check method calls
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in DANGEROUS_CALLS:
                        result.errors.append(f"Dangerous method call: .{node.func.attr}()")

    def _analyze_attributes(self, tree: ast.AST, result: ValidationResult) -> None:
        """Analyze attribute access for dangerous patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in DANGEROUS_ATTRIBUTES:
                    result.errors.append(f"Dangerous attribute access: .{node.attr}")

    def _verify_filter_structure(self, tree: ast.AST, result: ValidationResult) -> None:
        """Verify the code defines a proper filter class."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for BaseFilter inheritance
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseFilter":
                        result.has_base_filter = True
                        result.class_name = node.name
                        break
                    elif isinstance(base, ast.Attribute) and base.attr == "BaseFilter":
                        result.has_base_filter = True
                        result.class_name = node.name
                        break

                # Check for check() method
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "check":
                        # Verify signature: def check(self, signal_data: dict) -> FilterResult
                        args = item.args
                        if len(args.args) >= 2:  # self + signal_data
                            result.has_check_method = True
                        else:
                            result.warnings.append(
                                "check() method should have signature: check(self, signal_data: dict)"
                            )

    def _regex_checks(self, code: str, result: ValidationResult) -> None:
        """Additional regex-based security checks."""
        # Check for string-based dangerous patterns that AST might miss
        dangerous_patterns = [
            (r'os\.system', "os.system call detected"),
            (r'subprocess\.', "subprocess module usage detected"),
            (r'__builtins__', "__builtins__ access detected"),
            (r'\.popen\(', "popen() call detected"),
            (r'socket\.', "socket module usage detected"),
            (r'urllib\.', "urllib module usage detected"),
            (r'requests\.', "requests module usage detected"),
            (r'http\.', "http module usage detected"),
            (r'pickle\.', "pickle module usage detected"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                result.errors.append(message)

        # Check for suspicious string concatenation that might build dangerous code
        if re.search(r'["\']\s*\+\s*["\'].*exec|eval', code, re.IGNORECASE):
            result.warnings.append("Suspicious string concatenation near exec/eval")

    def validate_and_test(self, code: str) -> ValidationResult:
        """
        Validate code and attempt to load it in a sandboxed environment.

        Args:
            code: Python source code

        Returns:
            ValidationResult with detailed validation status
        """
        # First, do static validation
        result = self.validate(code)
        if not result.is_valid:
            return result

        # Try to compile the code
        try:
            compile(code, "<generated>", "exec")
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Compilation failed: {str(e)}")
            return result

        # Try to execute in restricted namespace
        try:
            namespace = self._create_sandbox_namespace()
            exec(compile(code, "<generated>", "exec"), namespace)

            # Verify the class was created
            filter_class = None
            for name, obj in namespace.items():
                if isinstance(obj, type) and name == result.class_name:
                    filter_class = obj
                    break

            if filter_class is None:
                result.warnings.append("Could not find filter class after execution")
            else:
                # Try to instantiate
                instance = filter_class()

                # Try to call check with dummy data
                dummy_signal = {
                    "instrument": "TEST_USD",
                    "direction": "LONG",
                    "confidence": 50,
                    "technical": {"trend": "NEUTRAL", "rsi": 50},
                    "sentiment": 0.0,
                    "session": "london",
                    "timestamp": None
                }

                check_result = instance.check(dummy_signal)
                if not hasattr(check_result, "passed"):
                    result.warnings.append("check() did not return a FilterResult")

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Execution test failed: {str(e)}")

        return result

    def _create_sandbox_namespace(self) -> dict:
        """Create a restricted namespace for code execution."""
        from datetime import datetime, timedelta, timezone
        from dataclasses import dataclass, field
        from typing import Dict, List, Optional, Any

        # Import BaseFilter and FilterResult
        try:
            from src.upgrade.base_filter import BaseFilter, FilterResult
        except ImportError:
            # For testing outside the project
            BaseFilter = object
            FilterResult = type("FilterResult", (), {"passed": True})

        return {
            "__builtins__": {
                "True": True,
                "False": False,
                "None": None,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "isinstance": isinstance,
                "hasattr": hasattr,  # Allow hasattr for basic checks
                "getattr": lambda obj, name, default=None: getattr(obj, name, default) if not name.startswith("_") else default,
            },
            "datetime": datetime,
            "timedelta": timedelta,
            "timezone": timezone,
            "dataclass": dataclass,
            "field": field,
            "Dict": Dict,
            "List": List,
            "Optional": Optional,
            "Any": Any,
            "BaseFilter": BaseFilter,
            "FilterResult": FilterResult,
        }
