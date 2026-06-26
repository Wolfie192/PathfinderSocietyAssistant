import json
import requests
import shutil
import os
import re
import streamlit as st

from pathlib import Path
from core.scenario_data import ScenarioData  # Import the new ScenarioData class
from modules.ImageModule import ImageModule
from modules.TextModule import TextModule
from modules.ReadAloudModule import ReadAloudModule
from modules.LineBreakModule import LineBreakModule
from modules.CharacterRosterModule import CharacterRosterModule
from modules.SkillCheckModule import SkillCheckModule
from modules.CombatEncounterModule import CombatEncounterModule


class ScenarioManager:
    """
    Class for managing scenario data and save states as the scenario is being run.
    Manages scenario data and save states as modules are added, modified, and/or deleted.
    """

    def __init__(self, season: str, scenario: str, root_dir: Path):
        # Define and create scenario-specific directories
        self.scenario_dir = root_dir / "data" / season / scenario
        self.scenario_dir.mkdir(parents=True, exist_ok=True)

        self.image_dir = self.scenario_dir / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

        self.monster_dir = self.scenario_dir / "monsters"
        self.monster_dir.mkdir(parents=True, exist_ok=True)

        # Store season and scenario identifiers
        self.season: str = season
        self.scenario: str = scenario

        # Retrieve scenario details using ScenarioData class for better encapsulation
        self.name: str = ScenarioData.get_scenario_name(self.season, self.scenario)
        self.tier_min: int = ScenarioData.get_scenario_tier_min(self.season, self.scenario)
        self.tier_max: int = ScenarioData.get_scenario_tier_max(self.season, self.scenario)

        # Initialize scenario data structure with a default main page
        self.scenario_data: dict = {"pages": [{"label": "Main Page", "modules": []}]}
        self.scenario_state: dict = {}  # Stores dynamic state during scenario play
        self.current_page = "landing_page"  # Initial page state

        self.root_dir = root_dir  # Store root_dir for passing to modules

        self.load()  # Load existing scenario data and state

    def load(self):
        """
        Method for loading the scenario_data and scenario_state when the scenario is selected.
        It attempts to load from JSON files; if not found or corrupted, it initializes defaults.
        """
        scenario_data_path = self.scenario_dir / "scenario_data.json"
        scenario_state_path = self.scenario_dir / "scenario_state.json"

        # Reset scenario_data to default before loading to ensure a clean state if loading fails
        self.scenario_data = {"pages": [{"label": "Main Page", "modules": []}]}

        if scenario_data_path.exists():
            with open(scenario_data_path, "r", encoding="utf-8") as f:
                try:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        # Handle legacy format where modules were directly under the root
                        if "modules" in loaded_data and "pages" not in loaded_data:
                            self.scenario_data["pages"] = [
                                {"label": "Main Page", "modules": loaded_data["modules"]}
                            ]
                        else:
                            self.scenario_data.update(loaded_data)
                except json.JSONDecodeError:
                    # If JSON is malformed, proceed with default scenario_data
                    pass

        if scenario_state_path.exists():
            with open(scenario_state_path, "r", encoding="utf-8") as f:
                self.scenario_state = json.load(f)
        else:
            # Initialize empty state if no state file exists
            self.scenario_state = {}

    def reset(self):
        """
        Method for resetting the scenario_state.
        Wipes all dynamic data like character rosters and combat states.
        """
        self.scenario_state = {}
        st.session_state.active_dialog = None  # Clear any active dialogs
        st.session_state.editing_module_data = None  # Clear any module being edited
        self.save()  # Persist the reset state

    def _module_save_callback(self):
        """
        Callback for modules to save their internal state and clear any dangling edit dialogs.
        This is called by individual modules when they make changes that need to be persisted.
        """
        st.session_state.active_dialog = None
        st.session_state.editing_module_data = None
        self.save()

    def save(self):
        """
        Method for saving the scenario_data and scenario_state when modifications are made.
        Writes the current scenario data and state to respective JSON files.
        """
        scenario_data_path = self.scenario_dir / "scenario_data.json"
        scenario_state_path = self.scenario_dir / "scenario_state.json"

        with open(scenario_data_path, "w", encoding="utf-8") as f:
            json.dump(self.scenario_data, f, indent=4)

        with open(scenario_state_path, "w", encoding="utf-8") as f:
            json.dump(self.scenario_state, f, indent=4)

    def _get_tier_mode(self):
        """
        Calculates the tier mode (Low/High) based on the total challenge points (CP)
        of the characters in the roster.
        """
        roster = self.scenario_state.get("roster", [])
        num_players = len(roster)
        total_cp = 0
        # CP mapping based on character level difference from scenario's minimum tier
        cp_map = {0: 2, 1: 3, 2: 4, 3: 6}

        for char in roster:
            level = char.get("level", self.tier_min)  # Default to min tier if level not found
            diff = int(level) - self.tier_min
            total_cp += cp_map.get(diff, 0)

        # Determine tier based on total CP and number of players
        if total_cp >= 19 or (num_players <= 4 and total_cp > 16):
            tier = "High"
        else:
            tier = "Low"

        self.scenario_state["total_cp"] = total_cp  # Store total CP in scenario state
        return tier, total_cp

    def _update_edit_mode_state(self):
        """
        Callback function to update st.session_state.edit_mode when the checkbox is toggled.
        """
        st.session_state.edit_mode = st.session_state.edit_mode_widget

    def run(self):
        """
        Method for initiating and running the scenario.
        Renders the sidebar navigation and the active page's modules.
        """
        # Display scenario title and tier in the sidebar
        st.sidebar.title(self.name)
        st.sidebar.markdown(f"**Tier:** {self.tier_min} - {self.tier_max}")
        st.sidebar.divider()

        # Calculate and display scenario scaling information
        tier_mode, total_cp = self._get_tier_mode()
        self.scenario_state["tier_mode"] = tier_mode  # Store tier mode in scenario state

        st.sidebar.subheader("Scenario Scaling")
        st.sidebar.markdown(f"**Total CP:** {total_cp}")
        st.sidebar.markdown(f"**Tier Mode:** {tier_mode}")
        st.sidebar.divider()

        st.sidebar.subheader("Pages")
        page_labels = [p["label"] for p in self.scenario_data["pages"]]

        # Ensure current_page_idx is valid, reset if out of bounds
        if "current_page_idx" not in self.scenario_state or self.scenario_state["current_page_idx"] >= len(page_labels):
            self.scenario_state["current_page_idx"] = 0

        # Streamlit radio button for page selection
        selected_page_label = st.sidebar.radio(
            "Select Page",
            page_labels,
            index=self.scenario_state["current_page_idx"],
            label_visibility="collapsed"
        )

        # Update current page index if a different page is selected
        new_idx = page_labels.index(selected_page_label)
        if new_idx != self.scenario_state["current_page_idx"]:
            self.scenario_state["current_page_idx"] = new_idx
            # Clear any active dialogs or editing states when switching pages
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            self.save()
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
            self.add_page_dialog()
        elif active_diag == "edit_page":
            self.edit_page_dialog()
        elif active_diag == "add_module":
            self.add_module_dialog()
        elif isinstance(active_diag, int):  # If active_dialog is an integer, it's a module index for editing
            # Initialize editing_module_data buffer if not already set
            if st.session_state.get("editing_module_data") is None:
                try:
                    current_modules = self.scenario_data["pages"][self.scenario_state["current_page_idx"]]["modules"]
                    st.session_state.editing_module_data = json.loads(json.dumps(current_modules[active_diag]))
                except (IndexError, KeyError):
                    # If index is invalid, clear dialog state and rerun
                    st.session_state.active_dialog = None
                    st.rerun()
            self.edit_module_dialog(active_diag)

        st.sidebar.divider()
        # Sidebar buttons for scenario reset and exit
        reset_col, exit_col = st.sidebar.columns(2)
        with reset_col:
            if st.button("Reset Scenario", use_container_width=True, help="Wipe all character and combat data"):
                self.reset()
                st.rerun()
        with exit_col:
            if st.button("Exit Scenario", use_container_width=True):
                self.save()  # Save current state before exiting
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
            on_change=self._update_edit_mode_state  # Callback to update st.session_state.edit_mode
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
        active_page = self.scenario_data["pages"][self.scenario_state["current_page_idx"]]
        modules = active_page.get("modules", [])

        if not modules:
            st.info("This page is empty. Click 'Add Module' to begin.")
            return

        for i, mod_data in enumerate(modules):
            self.render_module_row(i, mod_data)

    def render_module_row(self, index, module_data):
        """
        Renders a single module based on its type and provides an edit button.
        """
        with st.container(border=False):
            content_col, control_col = st.columns([0.95, 0.05])

            with content_col:
                # Instantiate and render the appropriate module based on its type
                if module_data["type"] == "image":
                    mod = ImageModule(
                        self.image_dir,
                        module_data.get("file"),
                        width=module_data.get("width") or 700
                    )
                    mod.render()
                elif module_data["type"] == "text":
                    mod = TextModule(module_data.get("content", ""))
                    mod.render()
                elif module_data["type"] == "read_aloud":
                    mod = ReadAloudModule(module_data.get("content", ""))
                    mod.render()
                elif module_data["type"] == "line_break":
                    mod = LineBreakModule(module_data.get("color", "#2e7d32"))
                    mod.render()
                elif module_data["type"] == "character_roster":
                    mod = CharacterRosterModule(
                        self.scenario_state,
                        self.tier_min,
                        self.tier_max,
                        self._module_save_callback
                    )
                    mod.render()
                elif module_data["type"] == "combat_encounter":
                    mod = CombatEncounterModule(
                        module_data,
                        self.scenario_state,
                        self.scenario_state.get("tier_mode", "Low"),
                        index,
                        self._module_save_callback,
                        self.monster_dir,
                        self.root_dir  # Pass root_dir here
                    )
                    mod.render()
                elif module_data["type"] == "skill_check":
                    mod = SkillCheckModule(
                        module_data,
                        self.scenario_state,
                        self.scenario_state.get("tier_mode", "Low"),
                        index,
                        self._module_save_callback
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

    @st.dialog("Add New Page")
    def add_page_dialog(self):
        """
        Streamlit dialog for adding a new page to the scenario.
        """
        new_label = st.text_input("Page Name", placeholder="e.g., Encounter A")
        if st.button("Create Page"):
            if new_label:
                self.scenario_data["pages"].append({"label": new_label, "modules": []})
                # Set the newly created page as the current active page
                self.scenario_state["current_page_idx"] = len(self.scenario_data["pages"]) - 1
                st.session_state.active_dialog = None
                self.save()
                st.rerun()

    @st.dialog("Edit Page Settings")
    def edit_page_dialog(self):
        """
        Streamlit dialog for editing the current page's settings (e.g., renaming, deleting).
        """
        idx = self.scenario_state["current_page_idx"]
        current_label = self.scenario_data["pages"][idx]["label"]

        new_label = st.text_input("Rename Page", value=current_label)
        if st.button("Update Label"):
            self.scenario_data["pages"][idx]["label"] = new_label
            st.session_state.active_dialog = None
            self.save()
            st.rerun()

        st.divider()
        if st.button("🗑️ Delete Entire Page", type="primary", use_container_width=True):
            if len(self.scenario_data["pages"]) > 1:
                self.scenario_data["pages"].pop(idx)
                st.session_state.active_dialog = None
                self.scenario_state["current_page_idx"] = 0  # Reset to first page after deletion
                self.save()
                st.rerun()
            else:
                st.error("You cannot delete the last remaining page.")

    def _process_external_image(self, source_path: str) -> str:
        """
        Helper to copy a local file or download a URL into the scenario image folder.
        Returns the filename if successful, or None if it fails.
        """
        try:
            filename = os.path.basename(source_path).split("?")[0]
            target_path = self.image_dir / filename

            if source_path.startswith(("http://", "https://")):
                response = requests.get(source_path, stream=True)
                response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                local_file = Path(source_path)
                if local_file.exists():
                    shutil.copy2(local_file, target_path)
                else:
                    st.error(f"Local file not found: {source_path}")
                    return None

            return filename
        except Exception as e:
            st.error(f"Failed to fetch image: {e}")
            return None

    def _parse_scribe_markdown(self, md_text: str):
        """
        Parses Pathfinder Scribe markdown for monster Name, HP, AC, and Initiative.
        """
        # Regex to extract Name (text after first '#')
        name_match = re.search(r"^#\s*(.*)", md_text, re.MULTILINE)
        # Regex to extract AC (number after **AC**)
        ac_match = re.search(r"\*\*AC\*\*\s*(\d+)", md_text)
        # Regex to extract HP (number after **HP**)
        hp_match = re.search(r"\*\*HP\*\*\s*(\d+)", md_text)
        # Regex to extract Initiative (first modifier (+/- X) after traits line)
        init_match = re.search(r"- ;.*?\n\*\*.*?\*\*\s*([+-]\d+)", md_text, re.DOTALL)

        return {
            "name": name_match.group(1).strip() if name_match else "Unknown Monster",
            "ac": ac_match.group(1) if ac_match else "N/A",
            "hp": int(hp_match.group(1)) if hp_match else 10,
            "init": int(init_match.group(1)) if init_match else 0
        }

    def _commit_module_change(self, module_data, insert_at=None):
        """
        Helper to save a new module and refresh the UI, reducing code repetition.
        """
        page_idx = self.scenario_state["current_page_idx"]
        modules = self.scenario_data["pages"][page_idx]["modules"]
        if insert_at is not None:
            modules.insert(insert_at, module_data)
        else:
            modules.append(module_data)
        st.session_state.active_dialog = None
        self.save()
        st.rerun()

    @st.dialog("Add Module")
    def add_module_dialog(self, insert_at=None):
        """
        Streamlit dialog pop-up to add a new module of various types.
        """
        mod_type = st.selectbox(
            "Module Type",
            ["text", "read_aloud", "image", "line_break", "character_roster", "skill_check", "combat_encounter"],
            format_func=lambda x: x.replace("_", " ").capitalize())

        if mod_type == "image":
            source_type = st.radio("Image Source", ["Existing", "Upload", "URL or Local Path"], horizontal=True)
            selected = None

            if source_type == "Existing":
                images = [f.name for f in self.image_dir.iterdir() if f.suffix in [".svg", ".png", ".jpg", ".jpeg"]]
                curr = images.index(selected) if selected in images else 0
                selected = st.selectbox("Select Image File", images)

            elif source_type == "Upload":
                uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "svg"])
                if uploaded_file:
                    target_path = self.image_dir / uploaded_file.name
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    selected = uploaded_file.name

            elif source_type == "URL or Local Path":
                external_path = st.text_input("Enter URL or Absolute Local Path")
                if external_path:
                    if st.button("Fetch and Preview"):
                        selected = self._process_external_image(external_path)
                        if selected:
                            st.success(f"Loaded: {selected}")

            st.write("Adjust Width")
            col_slider, col_input = st.columns([0.7, 0.3])
            with col_slider:
                width_s = st.slider("Width Slider", 100, 2000, 700, label_visibility="collapsed")
            with col_input:
                selected_width = st.number_input("Width Px", 100, 2000, width_s, label_visibility="collapsed")

            if st.button("Save"):
                if selected:
                    new_mod = {"type": "image", "file": selected, "width": selected_width}
                    self._commit_module_change(new_mod, insert_at)
                else:
                    st.warning("Please select or provide an image first.")

        elif mod_type == "text":
            content = st.text_area("Markdown Content", height=200, placeholder="Enter your text here...")

            if st.button("Save"):
                if content:
                    new_mod = {"type": "text", "content": content}
                    self._commit_module_change(new_mod, insert_at)
                else:
                    st.warning("Please enter some text first.")

        elif mod_type == "read_aloud":
            content = st.text_area("Read Aloud Content", height=200, placeholder="Enter text to be read aloud...")

            if st.button("Save"):
                if content:
                    new_mod = {"type": "read_aloud", "content": content}
                    self._commit_module_change(new_mod, insert_at)
                else:
                    st.warning("Please enter some text first.")

        elif mod_type == "line_break":
            color = st.color_picker("Line Color", value="#2e7d32")

            if st.button("Save"):
                new_mod = {"type": "line_break", "color": color}
                self._commit_module_change(new_mod, insert_at)

        elif mod_type == "character_roster":
            st.info("The Character Roster will manage 2-6 players and calculate Challenge Points automatically.")
            if st.button("Save"):
                new_mod = {"type": "character_roster"}
                self._commit_module_change(new_mod, insert_at)

        elif mod_type == "skill_check":
            is_secret = st.checkbox("Secret Check (GM Rolls Only)")
            st.info("Skills and DCs will be configured in the module edit (📝) settings after saving.")
            if st.button("Save"):
                new_mod = {"type": "skill_check", "is_secret": is_secret, "skills": []}
                self._commit_module_change(new_mod, insert_at)

        elif mod_type == "combat_encounter":
            st.info(
                "Combat encounters now come pre-configured with standard PFS scaling buckets (Low 0-18, High 0-36).")
            if st.button("Save"):
                default_scaling = [
                    {"tier": "Low", "min_cp": 0, "max_cp": 9, "monsters": []},
                    {"tier": "Low", "min_cp": 10, "max_cp": 11, "monsters": []},
                    {"tier": "Low", "min_cp": 12, "max_cp": 13, "monsters": []},
                    {"tier": "Low", "min_cp": 14, "max_cp": 15, "monsters": []},
                    {"tier": "Low", "min_cp": 16, "max_cp": 18, "monsters": []},
                    {"tier": "High", "min_cp": 0, "max_cp": 18, "monsters": []},
                    {"tier": "High", "min_cp": 19, "max_cp": 22, "monsters": []},
                    {"tier": "High", "min_cp": 23, "max_cp": 27, "monsters": []},
                    {"tier": "High", "min_cp": 28, "max_cp": 32, "monsters": []},
                    {"tier": "High", "min_cp": 33, "max_cp": 36, "monsters": []}
                ]
                new_mod = {"type": "combat_encounter", "scaling": default_scaling}
                self._commit_module_change(new_mod, insert_at)

    @st.dialog("Edit Module")
    def edit_module_dialog(self, index):
        """
        Streamlit dialog pop-up to modify an existing module.
        Allows editing module-specific properties and reordering modules.
        """
        page_idx = self.scenario_state["current_page_idx"]
        num_modules = len(self.scenario_data["pages"][page_idx]["modules"])

        # Guard clause: Ensure the index is valid for the current page and buffer exists
        if index >= num_modules or st.session_state.editing_module_data is None:
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            st.rerun()
            return

        # Use the buffered data for editing to avoid direct modification of live data
        mod_data = st.session_state.editing_module_data

        # Input for changing module position
        new_pos = st.number_input(
            "Module Position",
            min_value=1,
            max_value=num_modules,
            value=index + 1,
            key=f"edit_pos_{index}",
            help="Change the order of this module by setting its position number."
        )
        new_index = new_pos - 1

        if mod_data["type"] == "image":
            source_type = st.radio("Update Source", ["Existing", "Upload", "URL or Local Path"], horizontal=True,
                                   key=f"edit_img_src_{index}")
            selected = mod_data.get("file")

            if source_type == "Existing":
                images = [f.name for f in self.image_dir.iterdir() if f.suffix in [".svg", ".png", ".jpg", ".jpeg"]]
                curr = images.index(selected) if selected in images else 0
                selected = st.selectbox("Update Image File", images, index=curr)

            elif source_type == "Upload":
                uploaded_file = st.file_uploader("Upload new image", type=["png", "jpg", "jpeg", "svg"])
                if uploaded_file:
                    target_path = self.image_dir / uploaded_file.name
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    selected = uploaded_file.name

            elif source_type == "URL or Local Path":
                external_path = st.text_input("Enter URL or Absolute Local Path")
                if external_path:
                    if st.button("Fetch Image"):
                        result = self._process_external_image(external_path)
                        if result:
                            selected = result
                            st.success(f"Updated to: {selected}")

            st.write("Update Width")
            col_slider, col_input = st.columns([0.7, 0.3])
            with col_slider:
                width_s = st.slider("Width Slider", 100, 2000, mod_data.get("width", 700), label_visibility="collapsed",
                                    key=f"edit_img_w_s_{index}")
            with col_input:
                selected_width = st.number_input("Width Px", 100, 2000, width_s, label_visibility="collapsed",
                                                 key=f"edit_img_w_n_{index}")

            modules = self.scenario_data["pages"][page_idx]["modules"]
            if st.button("Update"):
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                    modules[new_index].update({"file": selected, "width": selected_width})
                else:
                    modules[index].update({"file": selected, "width": selected_width})

                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        elif mod_data["type"] == "text":
            new_content = st.text_area("Update Markdown Content", value=mod_data.get("content", ""), height=200,
                                       key=f"edit_text_{index}")

            modules = self.scenario_data["pages"][page_idx]["modules"]
            if st.button("Update"):
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                    modules[new_index]["content"] = new_content
                else:
                    modules[index]["content"] = new_content

                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        elif mod_data["type"] == "read_aloud":
            new_content = st.text_area("Update Read Aloud Content", value=mod_data.get("content", ""), height=200,
                                       key=f"edit_ra_{index}")

            modules = self.scenario_data["pages"][page_idx]["modules"]
            if st.button("Update"):
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                    modules[new_index]["content"] = new_content
                else:
                    modules[index]["content"] = new_content

                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        elif mod_data["type"] == "line_break":
            new_color = st.color_picker("Update Line Color", value=mod_data.get("color", "#2e7d32"),
                                        key=f"edit_lb_{index}")

            modules = self.scenario_data["pages"][page_idx]["modules"]
            if st.button("Update"):
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                modules[new_index if new_index != index else index]["color"] = new_color
                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        elif mod_data["type"] == "combat_encounter":
            mod_data["label"] = st.text_input("Module Label", value=mod_data.get("label", "⚔️ Combat Encounter"),
                                              key=f"edit_lbl_{index}")
            st.write("### ⚖️ Encounter Scaling Groups")

            for g_idx, group in enumerate(mod_data.get("scaling", [])):
                with st.expander(f"Group: {group['tier']} (CP {group['min_cp']}-{group['max_cp']})"):
                    st.write("#### Add Monster")
                    m_markdown = st.text_area("Paste Scribe Markdown", key=f"edit_{index}_mmd_{g_idx}", height=150,
                                              help="Stat block details will be parsed automatically.")

                    if st.button("Parse and Add Monster", key=f"edit_{index}_abm_{g_idx}"):
                        if m_markdown:
                            stats = self._parse_scribe_markdown(m_markdown)
                            group["monsters"].append({
                                "name": stats["name"],
                                "max_hp": stats["hp"],
                                "ac": stats["ac"],
                                "init_mod": stats["init"],
                                "markdown": m_markdown
                            })
                            st.rerun()
                        else:
                            st.warning("Please enter a name for the monster.")

                    st.write("---")
                    st.write("Monsters in this group:")
                    for m_idx, monster in enumerate(group.get("monsters", [])):
                        with st.container():
                            mc1, mc4 = st.columns([5, 1])
                            mc1.write(f"**{monster['name']}**")

                            # Allow editing existing markdown
                            new_m_md = st.text_area("Edit Markdown", value=monster.get("markdown", ""),
                                                    key=f"edit_md_{index}_{g_idx}_{m_idx}",
                                                    label_visibility="collapsed")
                            monster["markdown"] = new_m_md

                            if mc4.button("🗑️", key=f"edit_{index}_del_m_{g_idx}_{m_idx}"):
                                group["monsters"].pop(m_idx)
                                st.rerun()

            if st.button("Update Module"):
                modules = self.scenario_data["pages"][page_idx]["modules"]
                # Commit the buffered data back to the main scenario data
                modules[index] = st.session_state.editing_module_data
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        elif mod_data["type"] == "skill_check":
            mod_data["is_secret"] = st.checkbox("Secret Check (GM Rolls Only)", value=mod_data.get("is_secret", False),
                                                key=f"edit_sc_sec_{index}")
            default_label = f"🎲 {'Secret ' if mod_data['is_secret'] else ''}Skill Check"
            mod_data["label"] = st.text_input("Module Label", value=mod_data.get("label", default_label),
                                              key=f"edit_lbl_{index}")

            st.write("---")
            st.write("### Skill Configuration")

            st.write("#### Add New Skill")
            new_skill_name = st.text_input("Skill Name", key=f"new_skill_name_{index}")
            ac1, ac2 = st.columns(2)
            new_low = ac1.number_input("Low Tier DC", value=15, key=f"new_low_{index}")
            new_high = ac2.number_input("High Tier DC", value=20, key=f"new_high_{index}")

            if st.button("Add Skill", key=f"edit_{index}_add_skill"):
                if new_skill_name:
                    mod_data["skills"].append({
                        "name": new_skill_name, "low_dc": new_low, "high_dc": new_high
                    })
                    st.rerun()

            st.write("#### Current Skills")
            # Display and delete existing skills
            for s_idx, skill in enumerate(mod_data.get("skills", [])):
                sc1, sc2, sc3, sc4 = st.columns([4, 2, 2, 1])
                sc1.write(f"**{skill['name']}**")
                sc2.write(f"L: {skill['low_dc']}")
                sc3.write(f"H: {skill['high_dc']}")
                if sc4.button("🗑️", key=f"del_skill_{index}_{s_idx}"):
                    mod_data["skills"].pop(s_idx)
                    st.rerun()

            modules = self.scenario_data["pages"][page_idx]["modules"]
            if st.button("Update Module"):
                # Commit the buffered data
                modules[index] = st.session_state.editing_module_data
                if new_index != index:
                    module_to_move = modules.pop(index)
                    modules.insert(new_index, module_to_move)
                st.session_state.active_dialog = None
                st.session_state.editing_module_data = None
                self.save()
                st.rerun()

        st.divider()
        # Delete and Cancel buttons for the edit module dialog
        c_del, c_can = st.columns(2)
        if c_del.button("🗑️ Delete Module", type="primary", use_container_width=True):
            self.scenario_data["pages"][page_idx]["modules"].pop(index)
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            self.save()
            st.rerun()

        if c_can.button("Cancel", use_container_width=True):
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            # No save here, just refresh to close the dialog
            st.rerun()