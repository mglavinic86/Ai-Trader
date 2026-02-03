"""
Filter Registry for AI Trader Self-Upgrade System.

Manages all filters (builtin and AI-generated) and runs them in order.

Usage:
    from src.upgrade.filter_registry import FilterRegistry, get_filter_registry

    registry = get_filter_registry()
    result = registry.run_all_filters(signal_data)
    if not result.passed:
        print(f"Signal blocked by: {result.filter_name}")
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.upgrade.base_filter import BaseFilter, FilterResult
from src.utils.logger import logger


@dataclass
class FilterChainResult:
    """Result of running the entire filter chain."""
    passed: bool
    blocking_filter: Optional[str] = None
    reason: str = ""
    filters_run: int = 0
    total_filters: int = 0
    execution_time_ms: int = 0
    filter_results: List[FilterResult] = field(default_factory=list)


class FilterRegistry:
    """
    Registry and executor for all trading filters.

    Maintains a sorted list of filters and executes them in priority order.
    First filter to block a signal stops the chain (fail-fast).
    """

    def __init__(self):
        self._filters: Dict[str, BaseFilter] = {}
        self._sorted_filters: List[BaseFilter] = []
        self._needs_sort = False

        # Paths for filter discovery
        self._builtin_path = Path(__file__).parent.parent / "filters" / "builtin"
        self._ai_generated_path = Path(__file__).parent.parent / "filters" / "ai_generated"

        # Load builtin filters on init
        self._load_builtin_filters()

    def _load_builtin_filters(self) -> None:
        """Load all builtin filters from src/filters/builtin/."""
        if not self._builtin_path.exists():
            self._builtin_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created builtin filters directory: {self._builtin_path}")
            return

        for filter_file in self._builtin_path.glob("*.py"):
            if filter_file.name.startswith("_"):
                continue

            try:
                self._load_filter_from_file(filter_file, "builtin")
            except Exception as e:
                logger.error(f"Failed to load builtin filter {filter_file.name}: {e}")

    def load_ai_generated_filters(self) -> int:
        """
        Load all AI-generated filters from src/filters/ai_generated/.

        Returns:
            Number of filters loaded
        """
        if not self._ai_generated_path.exists():
            self._ai_generated_path.mkdir(parents=True, exist_ok=True)
            return 0

        loaded = 0
        for filter_file in self._ai_generated_path.glob("*.py"):
            if filter_file.name.startswith("_"):
                continue

            try:
                self._load_filter_from_file(filter_file, "ai_generated")
                loaded += 1
            except Exception as e:
                logger.error(f"Failed to load AI filter {filter_file.name}: {e}")

        if loaded > 0:
            logger.info(f"Loaded {loaded} AI-generated filters")

        return loaded

    def _load_filter_from_file(self, file_path: Path, filter_type: str) -> Optional[BaseFilter]:
        """
        Load a filter class from a Python file.

        Expects the file to define a class that inherits from BaseFilter.
        The class should be named with 'Filter' suffix (e.g., SpreadFilter).

        Args:
            file_path: Path to the filter Python file
            filter_type: 'builtin' or 'ai_generated'

        Returns:
            The instantiated filter or None
        """
        module_name = f"filter_{filter_type}_{file_path.stem}"

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del sys.modules[module_name]
            raise ImportError(f"Failed to execute module: {e}")

        # Find the filter class
        filter_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type) and
                issubclass(obj, BaseFilter) and
                obj is not BaseFilter
            ):
                filter_class = obj
                break

        if filter_class is None:
            raise ImportError(f"No BaseFilter subclass found in {file_path}")

        # Instantiate and register
        filter_instance = filter_class()
        filter_instance.filter_type = filter_type
        self.register(filter_instance)

        return filter_instance

    def register(self, filter_instance: BaseFilter) -> None:
        """
        Register a filter with the registry.

        Args:
            filter_instance: The filter to register
        """
        if filter_instance.name in self._filters:
            logger.warning(f"Filter '{filter_instance.name}' already registered, replacing")

        self._filters[filter_instance.name] = filter_instance
        self._needs_sort = True

        logger.debug(f"Registered filter: {filter_instance.name} (priority={filter_instance.priority})")

    def unregister(self, filter_name: str) -> bool:
        """
        Remove a filter from the registry.

        Args:
            filter_name: Name of the filter to remove

        Returns:
            True if filter was removed
        """
        if filter_name in self._filters:
            del self._filters[filter_name]
            self._needs_sort = True
            logger.info(f"Unregistered filter: {filter_name}")
            return True
        return False

    def get(self, filter_name: str) -> Optional[BaseFilter]:
        """Get a filter by name."""
        return self._filters.get(filter_name)

    def get_all(self) -> List[BaseFilter]:
        """Get all registered filters (sorted by priority)."""
        if self._needs_sort:
            self._sorted_filters = sorted(
                self._filters.values(),
                key=lambda f: f.priority
            )
            self._needs_sort = False
        return self._sorted_filters

    def get_enabled(self) -> List[BaseFilter]:
        """Get all enabled filters (sorted by priority)."""
        return [f for f in self.get_all() if f.is_enabled()]

    def run_all_filters(self, signal_data: dict) -> FilterChainResult:
        """
        Run all enabled filters on a signal.

        Filters are run in priority order. The chain stops at the first
        filter that blocks the signal (fail-fast).

        Args:
            signal_data: Signal data dictionary

        Returns:
            FilterChainResult with pass/fail status and details
        """
        start_time = datetime.now()
        enabled_filters = self.get_enabled()

        result = FilterChainResult(
            passed=True,
            total_filters=len(enabled_filters)
        )

        for filter_instance in enabled_filters:
            try:
                filter_result = filter_instance.check(signal_data)
                filter_result.filter_name = filter_instance.name
                result.filter_results.append(filter_result)
                result.filters_run += 1

                # Update filter stats
                filter_instance.update_stats(filter_result)

                if not filter_result.passed:
                    result.passed = False
                    result.blocking_filter = filter_instance.name
                    result.reason = filter_result.reason
                    break

            except Exception as e:
                logger.error(f"Filter '{filter_instance.name}' error: {e}")
                # Don't block on filter errors, log and continue
                continue

        result.execution_time_ms = int(
            (datetime.now() - start_time).total_seconds() * 1000
        )

        return result

    def enable_filter(self, filter_name: str) -> bool:
        """Enable a filter by name."""
        if filter_name in self._filters:
            self._filters[filter_name].enable()
            return True
        return False

    def disable_filter(self, filter_name: str) -> bool:
        """Disable a filter by name."""
        if filter_name in self._filters:
            self._filters[filter_name].disable()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all filters."""
        return {
            "total_filters": len(self._filters),
            "enabled_filters": len(self.get_enabled()),
            "builtin_count": len([f for f in self._filters.values() if f.filter_type == "builtin"]),
            "ai_generated_count": len([f for f in self._filters.values() if f.filter_type == "ai_generated"]),
            "filters": [f.get_stats() for f in self.get_all()]
        }

    def deploy_filter(self, filter_code: str, filter_name: str) -> bool:
        """
        Deploy a new AI-generated filter.

        Saves the filter code to the ai_generated directory and loads it.

        Args:
            filter_code: Python code for the filter
            filter_name: Name for the filter file (without .py)

        Returns:
            True if deployment succeeded
        """
        # Ensure directory exists
        self._ai_generated_path.mkdir(parents=True, exist_ok=True)

        filter_path = self._ai_generated_path / f"{filter_name}.py"

        try:
            # Write the filter code
            filter_path.write_text(filter_code, encoding="utf-8")

            # Load the filter
            self._load_filter_from_file(filter_path, "ai_generated")

            logger.info(f"Deployed new AI filter: {filter_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to deploy filter {filter_name}: {e}")
            # Clean up failed deployment
            if filter_path.exists():
                filter_path.unlink()
            return False

    def rollback_filter(self, filter_name: str) -> bool:
        """
        Remove and disable an AI-generated filter.

        Args:
            filter_name: Name of the filter to rollback

        Returns:
            True if rollback succeeded
        """
        # Find and remove from registry
        if filter_name in self._filters:
            filter_instance = self._filters[filter_name]

            # Only allow rollback of AI-generated filters
            if filter_instance.filter_type != "ai_generated":
                logger.warning(f"Cannot rollback builtin filter: {filter_name}")
                return False

            self.unregister(filter_name)

        # Remove the file
        filter_path = self._ai_generated_path / f"{filter_name}.py"
        if filter_path.exists():
            # Move to .rolled_back for audit
            rollback_path = filter_path.with_suffix(".py.rolled_back")
            filter_path.rename(rollback_path)
            logger.info(f"Rolled back filter: {filter_name}")
            return True

        return False


# Singleton registry instance
_registry_instance: Optional[FilterRegistry] = None


def get_filter_registry() -> FilterRegistry:
    """Get or create the global filter registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FilterRegistry()
    return _registry_instance
