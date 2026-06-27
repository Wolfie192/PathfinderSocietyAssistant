import streamlit as st
import json

from modules.ImageModule import ImageModule
from modules.TextModule import TextModule
from modules.ReadAloudModule import ReadAloudModule
from modules.LineBreakModule import LineBreakModule
from modules.CharacterRosterModule import CharacterRosterModule
from modules.SkillCheckModule import SkillCheckModule
from modules.CombatEncounterModule import CombatEncounterModule

from ui.scenario_editor_ui import add_page_dialog, edit_page_dialog, add_module_dialog, edit_module_dialog


def _calculate_tier_mode(scenario_manager_instance):
    """
    Calculates the tier mode (Low/High) based on the total challenge points (CP)
    of the characters in the roster.
    """
    roster = scenario_manager_instance.scenario_state.get("roster", [])
    num_players = len(roster)
    total_cp = 0
    # CP mapping based on character level difference from scenario's minimum tier
    cp_map = {0: 2, 1: 3, 2: 4, 3: 6}

    for char in roster:
        level = char.get("level", scenario_manager_instance.tier_min)  # Default to min tier if level not found
        diff = int(level) - scenario_manager_instance.tier_min
        total_cp += cp_map.get(diff, 0)

    # Determine tier based on total CP and number of players
    if total_cp >= 19 or (num_players <= 4 and total_cp > 16):
        tier = "High"
    else:
        tier = "Low"

    scenario_manager_instance.scenario_state["total_cp"] = total_cp  # Store total CP in scenario state
    # logger.debug(f"Calculated tier mode: {tier} (Total CP: {total_cp})") # Removed logger as it's a UI function
    return tier, total_cp


def render_module_row(scenario_manager_instance, index: int, module_data: dict):
    """
    Renders a single module based on its type and provides an edit button.
    """
    with st.container(border=False):
        content_col, control_col = st.columns([0.95, 0.05])

        with content_col:
            # Determine if bottom padding should be added for ReadAloudModule
            add_bottom_padding = True
            active_page = scenario_manager_instance.scenario_data["pages"][st.session_state["current_page_idx"]]
            modules = active_page.get("modules", [])
            if module_data["type"] == "read_aloud" and (index + 1) < len(modules):
                if modules[index + 1]["type"] == "read_aloud":
                    add_bottom_padding = False

            # Instantiate and render the appropriate module based on its type
            if module_data["type"] == "image":
                mod = ImageModule(
                    scenario_manager_instance.image_dir,
                    module_data.get("file"),
                    width=module_data.get("width") or 700
                )
                mod.render()
            elif module_data["type"] == "text":
                mod = TextModule(module_data.get("content", ""))
                mod.render()
            elif module_data["type"] == "read_aloud":
                mod = ReadAloudModule(module_data.get("content", ""))
                mod.render(add_bottom_padding=add_bottom_padding) # Pass the padding flag
            elif module_data["type"] == "line_break":
                mod = LineBreakModule(module_data.get("color", "#2e7d32"))
                mod.render()
            elif module_data["type"] == "character_roster":
                mod = CharacterRosterModule(
                    scenario_manager_instance.scenario_state,
                    scenario_manager_instance.tier_min,
                    scenario_manager_instance.tier_max,
                    scenario_manager_instance.save # Direct call to save
                )
                mod.render()
            elif module_data["type"] == "combat_encounter":
                mod = CombatEncounterModule(
                    module_data,
                    scenario_manager_instance.scenario_state,
                    scenario_manager_instance.scenario_state.get("tier_mode", "Low"),
                    index,
                    scenario_manager_instance.save, # Direct call to save
                    scenario_manager_instance.monster_dir,
                    scenario_manager_instance.root_dir
                )
                mod.render()
            elif module_data["type"] == "skill_check":
                mod = SkillCheckModule(
                    module_data,
                    scenario_manager_instance.scenario_state,
                    scenario_manager_instance.scenario_state.get("tier_mode", "Low"),
                    index,
                    scenario_manager_instance.save # Direct call to save
                )
                mod.render()

        with control_col:
            # Edit button for each module (conditional on edit mode)
            if st.session_state.edit_mode:
                if st.button("📝", key=f"edit_{index}", help="Edit this module"):
                    # Store a deep copy of the module data for editing to prevent direct modification
                    st.session_state.editing_module_data = json.loads(json.dumps(module_data))
                    st.session_state.active_dialog = index  # Set active dialog to the module's index
                    st.rerun()


def render_scenario_playback(scenario_manager_instance):
    """
    Renders the scenario playback interface, including sidebar navigation and active page modules.
    """
    # Display scenario title and tier in the sidebar
    st.sidebar.title(scenario_manager_instance.name)
    st.sidebar.markdown(f"**Tier:** {scenario_manager_instance.tier_min} - {scenario_manager_instance.tier_max}")
    st.sidebar.divider()

    # Calculate and display scenario scaling information
    tier_mode, total_cp = _calculate_tier_mode(scenario_manager_instance)
    scenario_manager_instance.scenario_state["tier_mode"] = tier_mode  # Store tier mode in scenario state

    st.sidebar.subheader("Scenario Scaling")
    st.sidebar.markdown(f"**Total CP:** {total_cp}")
    st.sidebar.markdown(f"**Tier Mode:** {tier_mode}")
    st.sidebar.divider()

    st.sidebar.subheader("Pages")
    page_labels = [p["label"] for p in scenario_manager_instance.scenario_data["pages"]]

    # Ensure current_page_idx is valid, reset if out of bounds
    if "current_page_idx" not in st.session_state or st.session_state["current_page_idx"] >= len(page_labels):
        st.session_state["current_page_idx"] = 0

    # Streamlit radio button for page selection
    selected_page_label = st.sidebar.radio(
        "Select Page",
        page_labels,
        index=st.session_state["current_page_idx"],
        label_visibility="collapsed"
    )

    # Update current page index if a different page is selected
    new_idx = page_labels.index(selected_page_label)
    if new_idx != st.session_state["current_page_idx"]:
        st.session_state["current_page_idx"] = new_idx
        # Clear any active dialogs or editing states when switching pages
        st.session_state.active_dialog = None
        st.session_state.editing_module_data = None
        scenario_manager_instance.save()
        st.rerun()

    # Sidebar buttons for page management (conditional on edit mode)
    if st.session_state.edit_mode:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("➕ Page", use_container_width=True):
                st.session_state.active_dialog = "add_page"
                st.rerun()
        with col2:
            if st.button("⚙️ Page", use_container_width=True):
                st.session_state.active_dialog = "edit_page"
                st.rerun()

    # Handle active dialogs (add page, edit page, add module, edit module)
    active_diag = st.session_state.get("active_dialog")
    if active_diag == "add_page":
        add_page_dialog(scenario_manager_instance)
    elif active_diag == "edit_page":
        edit_page_dialog(scenario_manager_instance)
    elif active_diag == "add_module":
        add_module_dialog(scenario_manager_instance)
    elif isinstance(active_diag, int):  # If active_dialog is an integer, it's a module index for editing
        # Initialize editing_module_data buffer if not already set
        if st.session_state.get("editing_module_data") is None:
            try:
                current_modules = scenario_manager_instance.scenario_data["pages"][st.session_state["current_page_idx"]]["modules"]
                st.session_state.editing_module_data = json.loads(json.dumps(current_modules[active_diag]))
            except (IndexError, KeyError):
                # If index is invalid, clear dialog state and rerun
                st.session_state.active_dialog = None
                st.rerun()
        edit_module_dialog(scenario_manager_instance, active_diag)

    st.sidebar.divider()
    # Sidebar buttons for scenario reset and exit
    reset_col, exit_col = st.sidebar.columns(2)
    with reset_col:
        if st.button("Reset Scenario", use_container_width=True, help="Wipe all character and combat data"):
            scenario_manager_instance.reset()
            st.rerun()
    with exit_col:
        if st.button("Exit Scenario", use_container_width=True):
            scenario_manager_instance.save()  # Save current state before exiting
            st.session_state.scenario_manager = None  # Clear scenario manager from session state
            if "current_scenario" in st.session_state:
                st.session_state.current_scenario = None  # Clear current scenario selection
            st.rerun()

    # --- Edit Mode Toggle ---
    st.sidebar.divider()
    st.sidebar.checkbox(
        "⚙️ Edit Mode",
        value=st.session_state.edit_mode,
        key="edit_mode_widget",  # Unique key for the widget
        on_change=lambda: setattr(st.session_state, "edit_mode", st.session_state.edit_mode_widget) # Direct update
    )
    # --- End Edit Mode Toggle ---

    # Button to add a new module to the current page (conditional on edit mode)
    if st.session_state.edit_mode:
        _, action_col = st.columns([0.9, 0.1])
        with action_col:
            if st.button("➕ Module", use_container_width=True):
                st.session_state.active_dialog = "add_module"
                st.rerun()

    # Render modules for the active page
    active_page = scenario_manager_instance.scenario_data["pages"][st.session_state["current_page_idx"]]
    modules = active_page.get("modules", [])

    if not modules:
        st.info("This page is empty. Click 'Add Module' to begin.")
        return

    for i, mod_data in enumerate(modules):
        render_module_row(scenario_manager_instance, i, mod_data)