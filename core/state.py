import streamlit as st


def init_session_state():
    """
    Initializes Streamlit's session state variables for the application.
    This function should be called once at the start of the application.
    """
    st.set_page_config(layout="wide", page_title="Pathfinder Society Assistant")

    # current_season: Stores the key of the currently selected season (e.g., "season_1", "quests").
    # Initialized to None, indicating no season is selected.
    if "current_season" not in st.session_state:
        st.session_state.current_season = None
    
    # current_scenario: Stores the key of the currently selected scenario within a season (e.g., "01", "00.1").
    # Initialized to None, indicating no scenario is selected.
    if "current_scenario" not in st.session_state:
        st.session_state.current_scenario = None
    
    # scenario_manager: Holds an instance of the ScenarioManager class once a scenario is loaded.
    # This object manages the active scenario's data and state.
    # Initialized to None, indicating no scenario is currently active.
    if "scenario_manager" not in st.session_state:
        st.session_state.scenario_manager = None
    
    # active_dialog: Stores the identifier for any currently open Streamlit dialog (e.g., "add_page", "edit_module").
    # Can also store an integer representing the index of a module being edited.
    # Initialized to None, indicating no dialog is active.
    if "active_dialog" not in st.session_state:
        st.session_state.active_dialog = None
    
    # editing_module_data: Temporarily stores a copy of module data when a module is being edited.
    # This acts as a buffer to allow modifications without directly affecting the live scenario data
    # until changes are committed.
    # Initialized to None.
    if "editing_module_data" not in st.session_state:
        st.session_state.editing_module_data = None

    # edit_mode: A boolean flag indicating whether the application is currently in edit mode.
    # When True, certain UI elements might become editable or additional controls might appear.
    # Initialized to False, meaning the application starts in view mode.
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False