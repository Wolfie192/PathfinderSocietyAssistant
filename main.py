import streamlit as st
from pathlib import Path

from core.directories import verify_directories
from core.scenario_manager import ScenarioManager
from core.scenario_data import ScenarioData # Import the new ScenarioData class
from core.state import init_session_state

# Import the new UI components
from ui.global_monster_ui import global_monsters_page
from ui.scenario_runner_ui import render_scenario_playback


def on_season_change():
    """
    Callback function for when the season selection changes.
    Resets the current scenario to None to ensure a valid selection.
    """
    st.session_state.current_scenario = None


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
    scenario_options = available_scenarios if current_season else ["No season selected"]
    scenario_disabled = not current_season

    current_scenario = st.selectbox(
        "Select Scenario",
        scenario_options,
        index=None,
        format_func=lambda x: f"{x}: {ScenarioData.get_scenario_name(current_season, x)}" if current_season else x,
        key="current_scenario",
        disabled=scenario_disabled
    )

    # Button to load the selected scenario
    # Disabled if no scenario is selected
    if st.button("Load Scenario", disabled=not current_scenario or scenario_disabled):
        # Initialize ScenarioManager with selected season, scenario, and root directory
        st.session_state.scenario_manager = ScenarioManager(current_season, current_scenario, root_dir)
        st.rerun() # Rerun the app to switch to the scenario view


def main(root_dir: Path):
    """
    Main function to run the Streamlit application.
    Checks if a scenario is loaded; if so, runs it, otherwise displays the main selection page.
    """
    if st.session_state.scenario_manager is not None:
        # Render the scenario playback UI
        render_scenario_playback(st.session_state.scenario_manager)
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