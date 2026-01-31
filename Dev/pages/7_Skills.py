"""
AI Trader - Skills & Knowledge Page

Browse and EDIT trading skills, knowledge base, and system prompt.
"""

import streamlit as st
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.core.settings_manager import settings_manager
from components.empty_states import render_minimal_status

st.set_page_config(page_title="Skills - AI Trader", page_icon="", layout="wide")


def save_file(file_path: Path, content: str) -> bool:
    """Save content to file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False


def main():
    st.title("Skills & Knowledge Editor")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["System Prompt", "Trading Skills", "Knowledge Base"])

    # === System Prompt Tab ===
    with tab1:
        st.subheader("System Prompt")
        st.caption("Definira osobnost i ponašanje AI asistenta")

        prompt_path = settings_manager.settings_dir / "system_prompt.md"

        # Load current content
        current_prompt = settings_manager.get_system_prompt()

        # Editor
        edited_prompt = st.text_area(
            "Edit System Prompt",
            value=current_prompt,
            height=400,
            key="system_prompt_editor"
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Save", type="primary", key="save_prompt"):
                if save_file(prompt_path, edited_prompt):
                    settings_manager._system_prompt = None  # Clear cache
                    st.success("System prompt saved!")
                    st.rerun()

        with col2:
            if st.button("Reset to Original", key="reset_prompt"):
                st.rerun()

        # Preview
        with st.expander("Preview (Markdown)"):
            st.markdown(edited_prompt)

    # === Skills Tab ===
    with tab2:
        st.subheader("Trading Skills")
        st.caption("Strategije i tehnike koje AI koristi za trading")

        skills = settings_manager.list_skills()
        skills_dir = settings_manager.skills_dir

        col1, col2 = st.columns([1, 3])

        with col1:
            st.markdown("### Skills")

            # List existing skills
            selected_skill = None
            for skill in skills:
                if st.button(f"📄 {skill}", key=f"skill_{skill}", use_container_width=True):
                    st.session_state.selected_skill = skill

            st.divider()

            # Add new skill
            st.markdown("### Add New")
            new_skill_name = st.text_input("Skill name", placeholder="e.g., breakout")
            if st.button("Create Skill", key="create_skill"):
                if new_skill_name:
                    new_path = skills_dir / f"{new_skill_name}.md"
                    if new_path.exists():
                        st.error("Skill already exists!")
                    else:
                        template = f"""# {new_skill_name.replace('_', ' ').title()}

## Opis
[Opis strategije]

## Kada koristiti
- [Uvjet 1]
- [Uvjet 2]

## Entry pravila
1. [Pravilo 1]
2. [Pravilo 2]

## Exit pravila
1. [Pravilo 1]
2. [Pravilo 2]

## Risk Management
- Stop Loss: [SL pravilo]
- Take Profit: [TP pravilo]
"""
                        if save_file(new_path, template):
                            st.success(f"Skill '{new_skill_name}' created!")
                            settings_manager._skills_cache = {}
                            st.rerun()

        with col2:
            # Edit selected skill
            selected = st.session_state.get("selected_skill", skills[0] if skills else None)

            if selected:
                st.markdown(f"### Editing: {selected}")

                skill_path = skills_dir / f"{selected}.md"
                skill_content = settings_manager.get_skill(selected) or ""

                edited_skill = st.text_area(
                    "Edit Skill",
                    value=skill_content,
                    height=400,
                    key=f"skill_editor_{selected}"
                )

                col_a, col_b, col_c = st.columns([1, 1, 3])

                with col_a:
                    if st.button("Save", type="primary", key=f"save_skill_{selected}"):
                        if save_file(skill_path, edited_skill):
                            settings_manager._skills_cache.pop(selected, None)
                            st.success("Skill saved!")
                            st.rerun()

                with col_b:
                    if st.button("Delete", key=f"delete_skill_{selected}"):
                        st.session_state.confirm_delete_skill = selected

                # Confirm delete
                if st.session_state.get("confirm_delete_skill") == selected:
                    st.warning(f"Delete '{selected}'?")
                    if st.button("YES, DELETE", type="primary"):
                        skill_path.unlink()
                        settings_manager._skills_cache.pop(selected, None)
                        st.session_state.selected_skill = None
                        st.session_state.confirm_delete_skill = None
                        st.success("Deleted!")
                        st.rerun()
                    if st.button("Cancel"):
                        st.session_state.confirm_delete_skill = None
                        st.rerun()

                # Preview
                with st.expander("Preview"):
                    st.markdown(edited_skill)
            else:
                st.info("Select a skill from the left or create a new one.")

    # === Knowledge Base Tab ===
    with tab3:
        st.subheader("Knowledge Base")
        st.caption("Domensko znanje i naučene lekcije")

        knowledge = settings_manager.get_all_knowledge()
        knowledge_names = list(knowledge.keys())
        knowledge_dir = settings_manager.knowledge_dir

        col1, col2 = st.columns([1, 3])

        with col1:
            st.markdown("### Knowledge Files")

            # List existing knowledge
            for name in knowledge_names:
                if st.button(f"📄 {name}", key=f"kb_{name}", use_container_width=True):
                    st.session_state.selected_kb = name

            st.divider()

            # Add new knowledge file
            st.markdown("### Add New")
            new_kb_name = st.text_input("File name", placeholder="e.g., trading_rules")
            if st.button("Create File", key="create_kb"):
                if new_kb_name:
                    new_path = knowledge_dir / f"{new_kb_name}.md"
                    if new_path.exists():
                        st.error("File already exists!")
                    else:
                        template = f"""# {new_kb_name.replace('_', ' ').title()}

## Sadržaj

[Dodaj znanje ovdje]

---
*Zadnje ažuriranje: danas*
"""
                        if save_file(new_path, template):
                            st.success(f"Knowledge file '{new_kb_name}' created!")
                            settings_manager._knowledge_cache = {}
                            st.rerun()

        with col2:
            # Edit selected knowledge
            selected_kb = st.session_state.get("selected_kb", knowledge_names[0] if knowledge_names else None)

            if selected_kb:
                st.markdown(f"### Editing: {selected_kb}")

                kb_path = knowledge_dir / f"{selected_kb}.md"
                kb_content = knowledge.get(selected_kb, "")

                edited_kb = st.text_area(
                    "Edit Knowledge",
                    value=kb_content,
                    height=400,
                    key=f"kb_editor_{selected_kb}"
                )

                col_a, col_b, col_c = st.columns([1, 1, 3])

                with col_a:
                    if st.button("Save", type="primary", key=f"save_kb_{selected_kb}"):
                        if save_file(kb_path, edited_kb):
                            settings_manager._knowledge_cache.pop(selected_kb, None)
                            st.success("Knowledge saved!")
                            st.rerun()

                with col_b:
                    if st.button("Delete", key=f"delete_kb_{selected_kb}"):
                        st.session_state.confirm_delete_kb = selected_kb

                # Confirm delete
                if st.session_state.get("confirm_delete_kb") == selected_kb:
                    st.warning(f"Delete '{selected_kb}'?")
                    if st.button("YES, DELETE", type="primary", key="confirm_del_kb"):
                        kb_path.unlink()
                        settings_manager._knowledge_cache.pop(selected_kb, None)
                        st.session_state.selected_kb = None
                        st.session_state.confirm_delete_kb = None
                        st.success("Deleted!")
                        st.rerun()
                    if st.button("Cancel", key="cancel_del_kb"):
                        st.session_state.confirm_delete_kb = None
                        st.rerun()

                # Preview
                with st.expander("Preview"):
                    st.markdown(edited_kb)
            else:
                st.info("Select a file from the left or create a new one.")

    # Minimal status bar
    render_minimal_status()


if __name__ == "__main__":
    main()
