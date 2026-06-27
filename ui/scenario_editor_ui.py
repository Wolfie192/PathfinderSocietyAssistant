import streamlit as st
from pathlib import Path

from core.utils import parse_scribe_markdown


# Helper function for image processing, moved from ScenarioManager
def _process_external_image(image_dir: Path, source_path: str) -> str:
    """
    Helper to copy a local file or download a URL into the scenario image folder.
    Returns the filename if successful, or None if it fails.
    """
    try:
        # Use Path.name to get the filename from the source_path
        filename = Path(source_path).name.split("?")[0]
        target_path = image_dir / filename

        if source_path.startswith(("http://", "https://")):
            st.error("Downloading images from URLs is not supported in this refactored version without 'requests'.")
            return None
        else:
            local_file = Path(source_path)
            if local_file.exists():
                # Use Path.write_bytes for copying
                target_path.write_bytes(local_file.read_bytes())
            else:
                st.error(f"Local file not found: {source_path}")
                return None

        return filename
    except Exception as e:
        st.error(f"Failed to fetch image: {e}")
        return None


@st.dialog("Add New Page")
def add_page_dialog(scenario_manager_instance):
    """
    Streamlit dialog for adding a new page to the scenario.
    """
    new_label = st.text_input("Page Name", placeholder="e.g., Encounter A")
    if st.button("Create Page"):
        if new_label:
            scenario_manager_instance.scenario_data["pages"].append({"label": new_label, "modules": []})
            # Set the newly created page as the current active page
            st.session_state["current_page_idx"] = len(scenario_manager_instance.scenario_data["pages"]) - 1
            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()

@st.dialog("Edit Page Settings")
def edit_page_dialog(scenario_manager_instance):
    """
    Streamlit dialog for editing the current page's settings (e.g., renaming, deleting, reordering).
    """
    idx = st.session_state["current_page_idx"]
    current_label = scenario_manager_instance.scenario_data["pages"][idx]["label"]
    num_pages = len(scenario_manager_instance.scenario_data["pages"])

    new_label = st.text_input("Rename Page", value=current_label)

    # Add number input for reordering
    new_pos = st.number_input(
        "Page Position",
        min_value=1,
        max_value=num_pages,
        value=idx + 1,
        key="page_position_input",
        help="Change the order of this page by setting its position number."
    )
    new_index = new_pos - 1 # Convert 1-based position to 0-based index

    if st.button("Update Page Settings"): # Renaming the button to be more general
        # Check if label changed
        label_changed = (new_label != current_label)
        # Check if position changed
        position_changed = (new_index != idx)

        if label_changed or position_changed:
            # Update label if it changed
            if label_changed:
                scenario_manager_instance.scenario_data["pages"][idx]["label"] = new_label

            # Reorder if position changed
            if position_changed:
                # Get the page data to move
                page_to_move = scenario_manager_instance.scenario_data["pages"].pop(idx)
                # Insert it at the new position
                scenario_manager_instance.scenario_data["pages"].insert(new_index, page_to_move)
                # Update the current_page_idx in scenario_state to reflect the new position
                st.session_state["current_page_idx"] = new_index

            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()
        else:
            st.warning("No changes detected.")

    st.divider()
    if st.button("🗑️ Delete Entire Page", type="primary", use_container_width=True):
        if len(scenario_manager_instance.scenario_data["pages"]) > 1:
            scenario_manager_instance.scenario_data["pages"].pop(idx)
            st.session_state.active_dialog = None
            # Adjust current_page_idx
            if len(scenario_manager_instance.scenario_data["pages"]) == 0:
                st.session_state["current_page_idx"] = 0
            elif idx >= len(scenario_manager_instance.scenario_data["pages"]): # If the last page was deleted
                st.session_state["current_page_idx"] = len(scenario_manager_instance.scenario_data["pages"]) - 1
            else: # If a middle page was deleted, the next page shifts into its spot
                st.session_state["current_page_idx"] = idx
            scenario_manager_instance.save()
            st.rerun()
        else:
            st.error("You cannot delete the last remaining page.")

    if st.button("Cancel", use_container_width=True, key="cancel_edit_page"):
        st.session_state.active_dialog = None
        st.rerun()


@st.dialog("Add Module")
def add_module_dialog(scenario_manager_instance, insert_at=None):
    """
    Streamlit dialog pop-up to add a new module of various types.
    """
    mod_type = st.selectbox(
        "Module Type",
        ["text", "read_aloud", "image", "line_break", "character_roster", "skill_check", "combat_encounter"],
        format_func=lambda x: x.replace("_", " ").capitalize())

    page_idx = st.session_state["current_page_idx"]
    modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]

    if mod_type == "image":
        source_type = st.radio("Image Source", ["Existing", "Upload", "URL or Local Path"], horizontal=True)
        selected = None

        if source_type == "Existing":
            images = [f.name for f in scenario_manager_instance.image_dir.iterdir() if f.suffix in [".svg", ".png", ".jpg", ".jpeg"]]
            curr = images.index(selected) if selected in images else 0
            selected = st.selectbox("Select Image File", images)

        elif source_type == "Upload":
            uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg", "svg"])
            if uploaded_file:
                target_path = scenario_manager_instance.image_dir / uploaded_file.name
                target_path.write_bytes(uploaded_file.getbuffer())
                selected = uploaded_file.name

        elif source_type == "URL or Local Path":
            external_path = st.text_input("Enter URL or Absolute Local Path")
            if external_path:
                if st.button("Fetch and Preview"):
                    # This still requires 'requests' for URL download.
                    # For now, I'll just handle local files.
                    if external_path.startswith(("http://", "https://")):
                        st.error("Downloading images from URLs is not supported in this refactored version.")
                        selected = None
                    else:
                        selected = _process_external_image(scenario_manager_instance.image_dir, external_path)
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
                if insert_at is not None:
                    modules.insert(insert_at, new_mod)
                else:
                    modules.append(new_mod)
                st.session_state.active_dialog = None
                scenario_manager_instance.save()
                st.rerun()
            else:
                st.warning("Please select or provide an image first.")

    elif mod_type == "text":
        content = st.text_area("Markdown Content", height=200, placeholder="Enter your text here...")

        if st.button("Save"):
            if content:
                new_mod = {"type": "text", "content": content}
                if insert_at is not None:
                    modules.insert(insert_at, new_mod)
                else:
                    modules.append(new_mod)
                st.session_state.active_dialog = None
                scenario_manager_instance.save()
                st.rerun()
            else:
                st.warning("Please enter some text first.")

    elif mod_type == "read_aloud":
        content = st.text_area("Read Aloud Content", height=200, placeholder="Enter text to be read aloud...")

        if st.button("Save"):
            if content:
                new_mod = {"type": "read_aloud", "content": content}
                if insert_at is not None:
                    modules.insert(insert_at, new_mod)
                else:
                    modules.append(new_mod)
                st.session_state.active_dialog = None
                scenario_manager_instance.save()
                st.rerun()
            else:
                st.warning("Please enter some text first.")

    elif mod_type == "line_break":
        color = st.color_picker("Line Color", value="#2e7d32")

        if st.button("Save"):
            new_mod = {"type": "line_break", "color": color}
            if insert_at is not None:
                modules.insert(insert_at, new_mod)
            else:
                modules.append(new_mod)
            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()

    elif mod_type == "character_roster":
        st.info("The Character Roster will manage 2-6 players and calculate Challenge Points automatically.")
        if st.button("Save"):
            new_mod = {"type": "character_roster"}
            if insert_at is not None:
                modules.insert(insert_at, new_mod)
            else:
                modules.append(new_mod)
            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()

    elif mod_type == "skill_check":
        is_secret = st.checkbox("Secret Check (GM Rolls Only)")
        st.info("Skills and DCs will be configured in the module edit (📝) settings after saving.")
        if st.button("Save"):
            new_mod = {"type": "skill_check", "is_secret": is_secret, "skills": []}
            if insert_at is not None:
                modules.insert(insert_at, new_mod)
            else:
                modules.append(new_mod)
            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()

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
            if insert_at is not None:
                modules.insert(insert_at, new_mod)
            else:
                modules.append(new_mod)
            st.session_state.active_dialog = None
            scenario_manager_instance.save()
            st.rerun()

@st.dialog("Edit Module")
def edit_module_dialog(scenario_manager_instance, index):
    """
    Streamlit dialog pop-up to modify an existing module.
    Allows editing module-specific properties and reordering modules.
    """
    page_idx = st.session_state["current_page_idx"]
    num_modules = len(scenario_manager_instance.scenario_data["pages"][page_idx]["modules"])

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
            images = [f.name for f in scenario_manager_instance.image_dir.iterdir() if f.suffix in [".svg", ".png", ".jpg", ".jpeg"]]
            curr = images.index(selected) if selected in images else 0
            selected = st.selectbox("Update Image File", images, index=curr)

        elif source_type == "Upload":
            uploaded_file = st.file_uploader("Upload new image", type=["png", "jpg", "jpeg", "svg"])
            if uploaded_file:
                target_path = scenario_manager_instance.image_dir / uploaded_file.name
                target_path.write_bytes(uploaded_file.getbuffer())
                selected = uploaded_file.name

        elif source_type == "URL or Local Path":
            external_path = st.text_input("Enter URL or Absolute Local Path")
            if external_path:
                if st.button("Fetch Image"):
                    if external_path.startswith(("http://", "https://")):
                        st.error("Downloading images from URLs is not supported in this refactored version.")
                        selected = None
                    else:
                        result = _process_external_image(scenario_manager_instance.image_dir, external_path)
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

        modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
        if st.button("Update"):
            # Update the buffered data with new values
            st.session_state.editing_module_data.update({"file": selected, "width": selected_width})

            # Commit the buffered data back to the main scenario data
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
            st.rerun()

    elif mod_data["type"] == "text":
        new_content = st.text_area("Update Markdown Content", value=mod_data.get("content", ""), height=200,
                                   key=f"edit_text_{index}")

        modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
        if st.button("Update"):
            st.session_state.editing_module_data["content"] = new_content
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)

            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
            st.rerun()

    elif mod_data["type"] == "read_aloud":
        new_content = st.text_area("Update Read Aloud Content", value=mod_data.get("content", ""), height=200,
                                   key=f"edit_ra_{index}")

        modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
        if st.button("Update"):
            st.session_state.editing_module_data["content"] = new_content
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)

            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
            st.rerun()

    elif mod_data["type"] == "line_break":
        new_color = st.color_picker("Update Line Color", value=mod_data.get("color", "#2e7d32"),
                                    key=f"edit_lb_{index}")

        modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
        if st.button("Update"):
            st.session_state.editing_module_data["color"] = new_color
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
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
                        stats = parse_scribe_markdown(m_markdown) # Use the imported function
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
            modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
            # Commit the buffered data back to the main scenario data
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
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

        modules = scenario_manager_instance.scenario_data["pages"][page_idx]["modules"]
        if st.button("Update Module"):
            # Commit the buffered data
            modules[index] = st.session_state.editing_module_data
            if new_index != index:
                module_to_move = modules.pop(index)
                modules.insert(new_index, module_to_move)
            st.session_state.active_dialog = None
            st.session_state.editing_module_data = None
            scenario_manager_instance.save()
            st.rerun()

    st.divider()
    # Delete and Cancel buttons for the edit module dialog
    c_del, c_can = st.columns(2)
    if c_del.button("🗑️ Delete Module", type="primary", use_container_width=True):
        scenario_manager_instance.scenario_data["pages"][page_idx]["modules"].pop(index)
        st.session_state.active_dialog = None
        st.session_state.editing_module_data = None
        scenario_manager_instance.save()
        st.rerun()

    if c_can.button("Cancel", use_container_width=True, key="cancel_edit_module"):
        st.session_state.active_dialog = None
        st.session_state.editing_module_data = None
        # No save here, just refresh to close the dialog
        st.rerun()