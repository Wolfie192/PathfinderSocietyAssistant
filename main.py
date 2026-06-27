import streamlit as st
import json
import re
from pathlib import Path

from core.directories import verify_directories
from core.scenario_manager import ScenarioManager
from core.scenario_data import ScenarioData # Import the new ScenarioData class
from core.state import init_session_state
from core.utils import parse_scribe_markdown # Import the shared utility function


def on_season_change():
    """
    Callback function for when the season selection changes.
    Resets the current scenario to None to ensure a valid selection.
    """
    st.session_state.current_scenario = None


@st.dialog("Add New Monster")
def add_monster_global_dialog(monster_dir: Path):
    """
    Streamlit dialog for adding a new monster globally.
    """
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


def main_page(root_dir: Path):
    """
    Renders the main page of the application, allowing users to select a season and scenario.
    """
    # Add "Add Monster" button
    if st.button("➕ Add Global Monster", use_container_width=True):
        st.session_state.active_dialog = "add_monster_global"
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
    # This is conditionally rendered based on whether a season is selected
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

    # Handle active dialogs
    active_diag = st.session_state.get("active_dialog")
    if active_diag == "add_monster_global":
        monster_dir = root_dir / "data" / "monsters"
        monster_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        add_monster_global_dialog(monster_dir)


def main(root_dir: Path):
    """
    Main function to run the Streamlit application.
    Checks if a scenario is loaded; if so, runs it, otherwise displays the main selection page.
    """
    if st.session_state.scenario_manager is not None:
        st.session_state.scenario_manager.run()
    else:
        main_page(root_dir)

if __name__ == "__main__":
    # Initialize Streamlit session state variables
    init_session_state()
    # Determine the root directory of the application
    root = Path(__file__).resolve().parent
    # Verify and create necessary directories
    verify_directories(root)
    # Run the main application logic
    main(root)