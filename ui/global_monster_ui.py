import streamlit as st
from pathlib import Path

from modules.scribe_formatter import ScribeFormatter
from core.monster_data import (
    load_all_global_monsters,
    save_global_monster,
    update_global_monster,
    delete_global_monster
)

@st.dialog("Add New Monster")
def add_monster_global_dialog(root_dir: Path):
    """
    Streamlit dialog for adding a new monster globally.
    """
    st.write("Paste the Pathfinder Scribe markdown for the monster below.")
    monster_markdown = st.text_area("Monster Scribe Markdown", height=300,
                                    placeholder="e.g., # Goblin\n**HP** 10\n**AC** 15\n...")

    if st.button("Parse and Save Monster"):
        if monster_markdown:
            try:
                monster_name = save_global_monster(root_dir, monster_markdown)
                st.success(f"Monster '{monster_name}' saved successfully!")
                st.session_state.active_dialog = None
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing or saving monster: {e}")
        else:
            st.warning("Please paste monster markdown to save.")

    if st.button("Cancel", key="cancel_add_monster_global"):
        st.session_state.active_dialog = None
        st.rerun()

@st.dialog("Edit Monster")
def edit_monster_global_dialog(root_dir: Path, monster_data: dict):
    """
    Streamlit dialog for editing an existing global monster.
    """
    original_filename = monster_data.get("_filename", "")
    original_markdown = monster_data.get("markdown", "")

    st.write(f"Editing Monster: **{monster_data.get('name', 'Unknown')}**")
    edited_markdown = st.text_area("Monster Scribe Markdown", value=original_markdown, height=300)

    if st.button("Update Monster"):
        if edited_markdown:
            try:
                updated_monster_name = update_global_monster(root_dir, original_filename, edited_markdown)
                st.success(f"Monster '{updated_monster_name}' updated successfully!")
                st.session_state.active_dialog = None
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing or saving monster: {e}")
        else:
            st.warning("Monster markdown cannot be empty.")

    if st.button("Cancel", key="cancel_edit_monster_global"):
        st.session_state.active_dialog = None
        st.rerun()

@st.dialog("Monster Stat Block Preview")
def preview_monster_stat_block_dialog(root_dir: Path, monster_name: str, monster_markdown: str):
    """
    Streamlit dialog to display a monster's full stat block preview.
    """
    st.write(f"### {monster_name}")
    if not monster_markdown:
        st.info(f"No stat block markdown provided for {monster_name}.")
        return

    scribe_formatter = ScribeFormatter(root_dir)
    formatted_html = scribe_formatter.format_markdown_to_html(monster_markdown, display_name=monster_name)
    st.markdown(formatted_html, unsafe_allow_html=True)

    if st.button("Close", key="close_preview_monster_global"):
        st.session_state.active_dialog = None
        st.rerun()


def global_monsters_page(root_dir: Path):
    """
    Renders the page for managing global monsters.
    """
    st.header("Global Monster Management")

    if st.button("⬅️ Back to Scenario Selection"):
        st.session_state.view = "main_page"
        st.session_state.active_dialog = None # Clear any open dialogs
        st.rerun()

    st.divider()

    if st.button("➕ Add New Monster", use_container_width=True):
        st.session_state.active_dialog = "add_monster_global"
        st.rerun()

    st.subheader("Existing Monsters")
    
    # Add search input
    search_query = st.text_input("Search monsters by name", key="monster_search_query")

    monsters = load_all_global_monsters(root_dir)
    
    # Filter monsters based on search query
    if search_query:
        monsters = [
            m for m in monsters if search_query.lower() in m.get("name", "").lower()
        ]

    if not monsters:
        if search_query:
            st.info(f"No monsters found matching '{search_query}'.")
        else:
            st.info("No global monsters found. Click 'Add New Monster' to create one.")
    else:
        for monster in monsters:
            name = monster.get("name", "Unknown Monster")
            filename = monster.get("_filename", "")
            markdown = monster.get("markdown", "")

            with st.container(border=True):
                col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                
                # Make monster name clickable for preview
                if col1.button(f"**{name}**", key=f"preview_monster_{filename}"):
                    st.session_state.active_dialog = "preview_monster_stat_block"
                    st.session_state.preview_monster_data = {"name": name, "markdown": markdown}
                    st.rerun()

                if col2.button("📝 Edit", key=f"edit_monster_{filename}"):
                    st.session_state.active_dialog = "edit_monster_global"
                    st.session_state.editing_monster_data = monster # Store data for dialog
                    st.rerun()
                if col3.button("🗑️ Delete", key=f"delete_monster_{filename}"):
                    if delete_global_monster(root_dir, filename):
                        st.success(f"Monster '{name}' deleted.")
                    else:
                        st.error(f"Failed to delete monster '{name}'.")
                    st.session_state.active_dialog = None # Close any open dialogs
                    st.rerun()

    # Handle active dialogs for this page
    active_diag = st.session_state.get("active_dialog")
    if active_diag == "add_monster_global":
        add_monster_global_dialog(root_dir)
    elif active_diag == "edit_monster_global":
        if st.session_state.get("editing_monster_data"):
            edit_monster_global_dialog(root_dir, st.session_state.editing_monster_data)
        else:
            st.session_state.active_dialog = None # Clear if no data
    elif active_diag == "preview_monster_stat_block":
        if st.session_state.get("preview_monster_data"):
            preview_monster_stat_block_dialog(
                root_dir,
                st.session_state.preview_monster_data["name"],
                st.session_state.preview_monster_data["markdown"]
            )
        else:
            st.session_state.active_dialog = None # Clear if no data