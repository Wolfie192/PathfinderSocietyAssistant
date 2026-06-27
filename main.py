import streamlit as st
import json
import re
from pathlib import Path
import os

from core.directories import verify_directories
from core.scenario_manager import ScenarioManager
from core.scenario_data import ScenarioData # Import the new ScenarioData class
from core.state import init_session_state
from core.utils import parse_scribe_markdown # Import the shared utility function
from modules.scribe_formatter import ScribeFormatter # Import ScribeFormatter


def on_season_change():
    """
    Callback function for when the season selection changes.
    Resets the current scenario to None to ensure a valid selection.
    """
    st.session_state.current_scenario = None

def _get_global_monster_dir(root_dir: Path) -> Path:
    """Helper to get the path to the global monsters directory."""
    monster_dir = root_dir / "data" / "monsters"
    monster_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists
    return monster_dir

def _load_all_global_monsters(root_dir: Path) -> list[dict]:
    """Loads all global monster data from JSON files."""
    monster_dir = _get_global_monster_dir(root_dir)
    monsters = []
    for monster_file in monster_dir.glob("*.json"):
        try:
            with open(monster_file, "r", encoding="utf-8") as f:
                monster_data = json.load(f)
                monster_data["_filename"] = monster_file.name # Store filename for edit/delete
                monsters.append(monster_data)
        except json.JSONDecodeError as e:
            st.warning(f"Could not load monster from {monster_file.name}: {e}")
        except Exception as e:
            st.warning(f"An error occurred loading monster {monster_file.name}: {e}")
    # Sort monsters alphabetically by name
    monsters.sort(key=lambda x: x.get("name", "Unknown Monster").lower())
    return monsters

def _delete_global_monster(root_dir: Path, filename: str):
    """Deletes a global monster JSON file."""
    monster_dir = _get_global_monster_dir(root_dir)
    file_path = monster_dir / filename
    if file_path.exists():
        os.remove(file_path)
        st.success(f"Monster '{filename.replace('.json', '').replace('_', ' ')}' deleted.")
    else:
        st.error(f"Monster file not found: {filename}")
    st.session_state.active_dialog = None # Close any open dialogs
    st.rerun()

@st.dialog("Add New Monster")
def add_monster_global_dialog(root_dir: Path):
    """
    Streamlit dialog for adding a new monster globally.
    """
    monster_dir = _get_global_monster_dir(root_dir)
    st.write("Paste the Pathfinder Scribe markdown for the monster below.")
    monster_markdown = st.text_area("Monster Scribe Markdown", height=300,
                                    placeholder="e.g., # Goblin\n**HP** 10\n**AC** 15\n...")

    if st.button("Parse and Save Monster"):
        if monster_markdown:
            try:
                monster_data = parse_scribe_markdown(monster_markdown) # Use the imported function
                monster_name = monster_data["name"]

                # Sanitize name for filename
                filename = "".join(c for c in monster_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
                filename = filename.replace(" ", "_") + ".json"
                file_path = monster_dir / filename

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(monster_data, f, indent=4)
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
    monster_dir = _get_global_monster_dir(root_dir)
    original_filename = monster_data["_filename"]
    original_markdown = monster_data.get("markdown", "")

    st.write(f"Editing Monster: **{monster_data.get('name', 'Unknown')}**")
    edited_markdown = st.text_area("Monster Scribe Markdown", value=original_markdown, height=300)

    if st.button("Update Monster"):
        if edited_markdown:
            try:
                updated_monster_data = parse_scribe_markdown(edited_markdown)
                updated_monster_name = updated_monster_data["name"]

                # Determine new filename (if name changed)
                new_filename = "".join(c for c in updated_monster_name if c.isalnum() or c in (' ', '.', '_')).rstrip()
                new_filename = new_filename.replace(" ", "_") + ".json"

                # If filename changed, delete old file
                if new_filename != original_filename:
                    old_file_path = monster_dir / original_filename
                    if old_file_path.exists():
                        os.remove(old_file_path)

                file_path = monster_dir / new_filename
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(updated_monster_data, f, indent=4)
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

    monsters = _load_all_global_monsters(root_dir)
    
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
            filename = monster.get("_filename")
            markdown = monster.get("markdown", "")

            with st.container(border=True):
                col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                
                # Make monster name clickable for preview
                if col1.button(f"**{name}**", key=f"preview_monster_{filename}", use_container_width=True):
                    st.session_state.active_dialog = "preview_monster_stat_block"
                    st.session_state.preview_monster_data = {"name": name, "markdown": markdown}
                    st.rerun()

                if col2.button("📝 Edit", key=f"edit_monster_{filename}"):
                    st.session_state.active_dialog = "edit_monster_global"
                    st.session_state.editing_monster_data = monster # Store data for dialog
                    st.rerun()
                if col3.button("🗑️ Delete", key=f"delete_monster_{filename}"):
                    _delete_global_monster(root_dir, filename)

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


def main_page(root_dir: Path):
    """
    Renders the main page of the application, allowing users to select a season and scenario.
    """
    if st.button("📚 Global Monsters", use_container_width=True):
        st.session_state.view = "global_monsters_page"
        st.session_state.active_dialog = None # Clear any open dialogs
        st.rerun()

    st.divider()

    # Retrieve available seasons using the ScenarioData class
    available_seasons = ScenarioData.get_available_seasons()

    # Streamlit selectbox for season selection
    current_season = st.selectbox(
        "Select Season",
        available_seasons,
        index=None,
        format_func=lambda x: x.replace("_", " ").capitalize(),
        key="current_season",
        on_change=on_season_change
    )

    available_scenarios = []
    if current_season:
        # Retrieve available scenarios for the selected season
        available_scenarios = list(ScenarioData.get_scenarios_for_season(current_season).keys())

    # Streamlit selectbox for scenario selection
    # This is conditionally rendered based on whether a season is chosen
    if current_season is not None:
        current_scenario = st.selectbox(
            "Select Scenario",
            available_scenarios,
            index=None,
            # Format function to display scenario key and name
            format_func=lambda x: f"{x}: {ScenarioData.get_scenario_name(current_season, x)}",
            key="current_scenario",
        )
    else:
        # Display a disabled selectbox if no season is chosen
        current_scenario = st.selectbox(
            "Select Scenario",
            ["No season selected"],
            disabled=True
        )

    # Button to load the selected scenario
    # Disabled if no scenario is selected
    if st.button("Load Scenario", disabled=not current_scenario):
        # Initialize ScenarioManager with selected season, scenario, and root directory
        st.session_state.scenario_manager = ScenarioManager(current_season, current_scenario, root_dir)
        st.rerun() # Rerun the app to switch to the scenario view


def main(root_dir: Path):
    """
    Main function to run the Streamlit application.
    Checks if a scenario is loaded; if so, runs it, otherwise displays the main selection page.
    """
    if st.session_state.scenario_manager is not None:
        st.session_state.scenario_manager.run()
    else:
        if "view" not in st.session_state:
            st.session_state.view = "main_page"

        if st.session_state.view == "main_page":
            main_page(root_dir)
        elif st.session_state.view == "global_monsters_page":
            global_monsters_page(root_dir)


if __name__ == "__main__":
    # Initialize Streamlit session state variables
    init_session_state()
    # Determine the root directory of the application
    root = Path(__file__).resolve().parent
    # Verify and create necessary directories
    verify_directories(root)
    # Run the main application logic
    main(root)