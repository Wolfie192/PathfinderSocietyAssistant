from modules.BaseModel import BaseModel
import streamlit as st
import random

class SkillCheckModule(BaseModel):
    """
    Module for handling secret and normal skill checks for characters within a scenario.
    It allows GMs to configure skills with different DCs for low and high tiers,
    and provides an interface for players (or GM for secret checks) to perform rolls.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, module_data: dict, scenario_state: dict, tier_mode: str, module_id: int, save_callback):
        """
        Initializes the SkillCheckModule.

        Args:
            module_data (dict): Configuration data for this specific skill check module.
                                Expected to contain 'skills' (list of skill configs) and 'is_secret' (boolean).
            scenario_state (dict): The global state of the current scenario, used for storing
                                   and retrieving character roster and skill check results.
            tier_mode (str): The current tier mode of the scenario ("Low" or "High"),
                             which influences the DC used for skill checks.
            module_id (int): A unique identifier for this module instance within the scenario.
            save_callback (callable): A function to call when the module's state changes
                                      and needs to be persisted to the scenario_state.
        """
        super().__init__()
        self.module_data = module_data
        self.scenario_state = scenario_state
        self.tier_mode = tier_mode # "Low" or "High"
        self.module_id = module_id
        self.save_callback = save_callback
        self.skills_config = module_data.get("skills", []) # List of {name, low_dc, high_dc}
        self.is_secret = module_data.get("is_secret", False)

        # Initialize storage for this specific module in scenario_state
        # This ensures that skill check results are persistent across reruns
        if "skill_check_data" not in self.scenario_state:
            self.scenario_state["skill_check_data"] = {}
        self.mod_key = str(self.module_id)
        if self.mod_key not in self.scenario_state["skill_check_data"]:
            self.scenario_state["skill_check_data"][self.mod_key] = {}
        
        self.storage = self.scenario_state["skill_check_data"][self.mod_key]

    def _calculate_result(self, total: int, dc: int, roll_val: int) -> int:
        """
        Calculates the degree of success for a Pathfinder 2e style skill check.

        Args:
            total (int): The total result of the skill check (roll + modifier).
            dc (int): The Difficulty Class of the skill check.
            roll_val (int): The natural die roll (d20) before modifiers.

        Returns:
            int: An integer representing the degree of success:
                 0 for Critical Failure, 1 for Failure, 2 for Success, 3 for Critical Success.
        """
        # Base step based on the numerical total
        if total >= dc + 10:
            step = 3 # Crit Success
        elif total >= dc:
            step = 2 # Success
        elif total <= dc - 10:
            step = 0 # Crit Failure
        else:
            step = 1 # Failure

        # Adjust degree by one step for Natural 20 or Natural 1
        if roll_val == 20:
            step = min(3, step + 1) # Natural 20 improves degree of success by one step
        elif roll_val == 1:
            step = max(0, step - 1) # Natural 1 worsens degree of success by one step

        return step

    def render(self):
        """
        Renders the skill check module in the Streamlit application.
        Displays character roster, skill selection, roll inputs, and results.
        Handles both secret (GM rolls) and normal (player inputs) skill checks.
        """
        default_label = f"🎲 {'Secret ' if self.is_secret else ''}Skill Check"
        display_label = self.module_data.get("label") or default_label
        
        # Use an expander for cleaner UI, especially when many modules are present
        with st.expander(display_label, expanded=False):
            roster = self.scenario_state.get("roster", [])
            if not roster:
                st.warning("No characters found in roster. Please add characters first.")
                return

            skill_names = [s["name"] for s in self.skills_config]
            
            if not skill_names:
                st.info("No skills configured. Click the edit (📝) button to add skills to this module.")
                return

            # Define column layout and headers based on whether it's a secret check
            if self.is_secret:
                cols = st.columns([2, 2.5, 1.5, 1, 1, 2.5])
                header_map = ["Character", "Skill (DC)", "Modifier", "Roll", "Total", "Result"]
            else:
                cols = st.columns([2, 2.5, 1.5, 3, 2.5])
                header_map = ["Character", "Skill (DC)", "Total Roll", "Natural?", "Result"]

            # Display column headers
            cols[0].caption("Character")
            cols[1].caption("Skill (DC)")
            cols[2].caption(header_map[2])
            cols[3].caption(header_map[3])
            if self.is_secret:
                cols[4].caption(header_map[4])
                cols[5].caption(header_map[5])
            else:
                cols[4].caption(header_map[4])

            # Outcome Mapping for displaying results with colors
            outcome_data = {
                0: ("Critical Failure", "#d32f2f"), # Red
                1: ("Failure", "#f57c00"),          # Orange
                2: ("Success", "#388e3c"),          # Green
                3: ("Critical Success", "#1b5e20")  # Dark Green
            }

            # Iterate through each character in the roster to display their skill check row
            for i, char in enumerate(roster):
                char_name = char.get("char") or char.get("player") or f"Player {i+1}"
                row_key = f"sc_{self.module_id}_{i}" # Unique key for Streamlit widgets in this row
                
                with st.container(): # Use a container to group elements for each character row
                    if self.is_secret:
                        c1, c2, c3, c4, c5, c6 = st.columns([2, 2.5, 1.5, 1, 1, 2.5])
                    else:
                        c1, c2, c3, c4, c5 = st.columns([2, 2.5, 1.5, 3, 2.5])
                    
                    c1.write(f"**{char_name}**")
                    
                    # Skill Selection (persistent via self.storage)
                    stored_skill = self.storage.get(f"skill_{i}")
                    skill_idx = skill_names.index(stored_skill) if stored_skill in skill_names else None
                    
                    sel_skill = c2.selectbox(
                        "Skill", skill_names, index=skill_idx, placeholder="Skill...", 
                        key=f"skill_sel_{self.module_id}_{i}", label_visibility="collapsed"
                    )
                    
                    # If skill selection changes, update storage and rerun to reflect DC change
                    if sel_skill != stored_skill:
                        self.storage[f"skill_{i}"] = sel_skill
                        self.save_callback()
                        st.rerun()

                    # Calculate DC based on selected skill and current tier mode
                    skill_cfg = next((s for s in self.skills_config if s["name"] == sel_skill), None)
                    dc = (skill_cfg["low_dc"] if self.tier_mode == "Low" else skill_cfg["high_dc"]) if skill_cfg else 0
                    
                    if sel_skill:
                        c2.caption(f"DC: {dc}")

                    if self.is_secret:
                        # For secret checks, GM inputs modifier and the roll is generated
                        # Modifier Input (persistent)
                        stored_mod = self.storage.get(f"mod_{i}")
                        mod = c3.number_input("Mod", value=stored_mod, step=1, key=f"{row_key}_mod", label_visibility="collapsed", placeholder="Mod")
                        
                        if mod != stored_mod:
                            self.storage[f"mod_{i}"] = mod
                            self.save_callback()
                        
                        # Secret Roll (generated and persistent)
                        if f"roll_{i}" not in self.storage:
                            self.storage[f"roll_{i}"] = random.randint(1, 20)
                            self.save_callback()
                        
                        roll = self.storage[f"roll_{i}"]
                        
                        if sel_skill and mod is not None:
                            total = roll + mod
                            final_step = self._calculate_result(total, dc, roll)
                            res_text, res_color = outcome_data[final_step]

                            c4.write(f"**{roll}**")
                            c5.write(str(total))
                            c6.markdown(f"**<span style='color:{res_color}'>{res_text}</span>**", unsafe_allow_html=True)
                        else:
                            c4.write("-")
                            c5.write("-")
                            c6.write("-")
                    else:
                        # For normal checks, player inputs total and natural status
                        # Manual Total Input (persistent)
                        stored_total = self.storage.get(f"total_{i}")
                        total_input = c3.number_input("Total", value=stored_total, step=1, key=f"{row_key}_total", label_visibility="collapsed", placeholder="Total")
                        
                        if total_input != stored_total:
                            self.storage[f"total_{i}"] = total_input
                            self.save_callback()

                        # Natural Roll Status (persistent)
                        stored_nat = self.storage.get(f"nat_{i}", "None")
                        nat_options = ["None", "Nat 1", "Nat 20"]
                        nat_idx = nat_options.index(stored_nat) if stored_nat in nat_options else 0
                        
                        nat_status = c4.radio(
                            "Nat", nat_options, 
                            index=nat_idx, key=f"{row_key}_nat", 
                            label_visibility="collapsed", horizontal=True
                        )
                        
                        if nat_status != stored_nat:
                            self.storage[f"nat_{i}"] = nat_status
                            self.save_callback()

                        if sel_skill and total_input is not None:
                            # Determine effective roll_val for degree of success calculation
                            roll_val = 20 if nat_status == "Nat 20" else (1 if nat_status == "Nat 1" else 10) # 10 is arbitrary for non-nat rolls
                            final_step = self._calculate_result(total_input, dc, roll_val)
                            res_text, res_color = outcome_data[final_step]
                            c5.markdown(f"**<span style='color:{res_color}'>{res_text}</span>**", unsafe_allow_html=True)
                        else:
                            c5.write("-")

            # Button to re-roll all secret checks at once
            if self.is_secret:
                if st.button("🔄 Re-roll Secret Checks", key=f"reroll_{self.module_id}"):
                    for i in range(len(roster)):
                        self.storage[f"roll_{i}"] = random.randint(1, 20)
                    self.save_callback()
                    st.rerun()