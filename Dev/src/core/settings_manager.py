"""
Settings Manager - Loads system prompt, skills, and knowledge.

Usage:
    from src.core.settings_manager import settings_manager

    # Get system prompt with all context
    prompt = settings_manager.get_full_system_prompt()

    # Get specific skill
    skill = settings_manager.get_skill("scalping")

    # Get all knowledge
    knowledge = settings_manager.get_all_knowledge()
"""

import json
from pathlib import Path
from typing import Optional
from src.utils.logger import logger


class SettingsManager:
    """Manages AI settings, skills, and knowledge base."""

    def __init__(self, settings_dir: Optional[Path] = None):
        """
        Initialize settings manager.

        Args:
            settings_dir: Path to settings folder
        """
        if settings_dir is None:
            self.settings_dir = Path(__file__).parent.parent.parent / "settings"
        else:
            self.settings_dir = settings_dir

        self.skills_dir = self.settings_dir / "skills"
        self.knowledge_dir = self.settings_dir / "knowledge"

        self._config = None
        self._config_mtime = None
        self._system_prompt = None
        self._skills_cache = {}
        self._knowledge_cache = {}

        self._load_config()
        logger.info(f"SettingsManager initialized: {self.settings_dir}")

    def _load_config(self) -> None:
        """Load config.json."""
        config_path = self.settings_dir / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self._config_mtime = config_path.stat().st_mtime
        else:
            self._config = {}
            self._config_mtime = None
            logger.warning("config.json not found, using defaults")

    def _reload_config_if_changed(self) -> None:
        """Reload config.json only if it changed on disk."""
        config_path = self.settings_dir / "config.json"
        if not config_path.exists():
            return
        try:
            current_mtime = config_path.stat().st_mtime
            if self._config is None or self._config_mtime is None or current_mtime != self._config_mtime:
                self._load_config()
                logger.info("Config reloaded from disk")
        except Exception as e:
            logger.warning(f"Could not check config changes: {e}")

    def get_config(self, key: str = None, default=None):
        """
        Get configuration value.

        Args:
            key: Dot-notation key (e.g., "ai.temperature")
            default: Default value if key not found

        Returns:
            Config value or entire config if key is None
        """
        self._reload_config_if_changed()

        if key is None:
            return self._config

        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_system_prompt(self) -> str:
        """
        Get the main system prompt.

        Returns:
            Content of system_prompt.md
        """
        if self._system_prompt is None:
            prompt_path = self.settings_dir / "system_prompt.md"
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    self._system_prompt = f.read()
            else:
                self._system_prompt = "You are a forex trading assistant."
                logger.warning("system_prompt.md not found")

        return self._system_prompt

    def get_skill(self, skill_name: str) -> Optional[str]:
        """
        Get a specific skill content.

        Args:
            skill_name: Name of the skill (without .md)

        Returns:
            Skill content or None if not found
        """
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        skill_path = self.skills_dir / f"{skill_name}.md"
        if skill_path.exists():
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._skills_cache[skill_name] = content
                return content

        return None

    def get_all_skills(self) -> dict[str, str]:
        """
        Get all available skills.

        Returns:
            Dict of skill_name -> content
        """
        skills = {}
        if self.skills_dir.exists():
            for skill_file in self.skills_dir.glob("*.md"):
                if skill_file.name != "README.md":
                    skill_name = skill_file.stem
                    with open(skill_file, "r", encoding="utf-8") as f:
                        skills[skill_name] = f.read()

        return skills

    def list_skills(self) -> list[str]:
        """Get list of available skill names."""
        skills = []
        if self.skills_dir.exists():
            for skill_file in self.skills_dir.glob("*.md"):
                if skill_file.name != "README.md":
                    skills.append(skill_file.stem)
        return skills

    def get_knowledge(self, name: str) -> Optional[str]:
        """
        Get a specific knowledge file content.

        Args:
            name: Name of the knowledge file (without .md)

        Returns:
            Content or None if not found
        """
        if name in self._knowledge_cache:
            return self._knowledge_cache[name]

        knowledge_path = self.knowledge_dir / f"{name}.md"
        if knowledge_path.exists():
            with open(knowledge_path, "r", encoding="utf-8") as f:
                content = f.read()
                self._knowledge_cache[name] = content
                return content

        return None

    def get_all_knowledge(self) -> dict[str, str]:
        """
        Get all knowledge base content.

        Returns:
            Dict of name -> content
        """
        knowledge = {}
        if self.knowledge_dir.exists():
            for kb_file in self.knowledge_dir.glob("*.md"):
                if kb_file.name != "README.md":
                    name = kb_file.stem
                    with open(kb_file, "r", encoding="utf-8") as f:
                        knowledge[name] = f.read()

        return knowledge

    def get_full_system_prompt(self, include_skills: list[str] = None) -> str:
        """
        Get complete system prompt with skills and knowledge.

        Args:
            include_skills: List of skills to include (None = enabled skills from config)

        Returns:
            Complete prompt string
        """
        parts = []

        # Main system prompt
        parts.append(self.get_system_prompt())

        # Add enabled skills
        if include_skills is None:
            include_skills = self.get_config("skills.enabled", [])
            include_skills.extend(self.get_config("skills.custom", []))

        for skill_name in include_skills:
            skill_content = self.get_skill(skill_name)
            if skill_content:
                parts.append(f"\n\n---\n\n## Skill: {skill_name}\n\n{skill_content}")

        # Add knowledge base
        knowledge = self.get_all_knowledge()
        if knowledge:
            parts.append("\n\n---\n\n## Knowledge Base\n")
            for name, content in knowledge.items():
                parts.append(f"\n### {name}\n\n{content}")

        return "\n".join(parts)

    def reload(self) -> None:
        """Reload all settings from disk."""
        self._config = None
        self._config_mtime = None
        self._system_prompt = None
        self._skills_cache = {}
        self._knowledge_cache = {}
        self._load_config()
        logger.info("Settings reloaded")

    def save_config(self) -> None:
        """Save current config to disk."""
        config_path = self.settings_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)
        logger.info("Config saved")

    def add_lesson(self, lesson_text: str) -> None:
        """
        Add a new lesson to lessons.md.

        Args:
            lesson_text: The lesson content to add
        """
        lessons_path = self.knowledge_dir / "lessons.md"

        if lessons_path.exists():
            with open(lessons_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "# Naučene Lekcije\n\n"

        # Find insertion point (before the last line)
        insert_marker = "<!-- Dodaj nove lekcije iznad ove linije -->"
        if insert_marker in content:
            content = content.replace(
                insert_marker,
                f"{lesson_text}\n\n{insert_marker}"
            )
        else:
            content += f"\n\n{lesson_text}"

        with open(lessons_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Clear cache
        self._knowledge_cache.pop("lessons", None)
        logger.info("Lesson added to knowledge base")


# Singleton instance
settings_manager = SettingsManager()
