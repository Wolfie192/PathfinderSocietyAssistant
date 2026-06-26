from modules.BaseModel import BaseModel
import streamlit as st
import random
from pathlib import Path
import uuid

class CombatEncounterModule(BaseModel):
    """
    Module for tracking initiative and monster health with dynamic scaling based on scenario tier.
    It provides an interface for GMs to manage combat participants (players and monsters),
    track initiative, health, and apply damage/healing.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, module_data: dict, scenario_state: dict, tier_mode: str, module_id: int, save_callback, monster_dir: Path):
        """
        Initializes the CombatEncounterModule.

        Args:
            module_data (dict): Configuration data for this specific combat encounter module.
                                Expected to contain 'scaling' groups for monsters.
            scenario_state (dict): The global state of the current scenario, used for storing
                                   and retrieving combat participants and their states.
            tier_mode (str): The current tier mode of the scenario ("Low" or "High"),
                             which determines which monster scaling group to use.
            module_id (int): A unique identifier for this module instance within the scenario.
            save_callback (callable): A function to call when the module's state changes
                                      and needs to be persisted to the scenario_state.
            monster_dir (Path): The directory where monster stat blocks (if any) are stored.
        """
        super().__init__()
        self.module_data = module_data
        self.scenario_state = scenario_state
        self.tier_mode = tier_mode
        self.module_id = module_id
        self.save_callback = save_callback
        self.monster_dir = monster_dir
        
        # Initialize persistent storage for this specific combat module within scenario_state
        if "combat_state" not in self.scenario_state:
            self.scenario_state["combat_state"] = {}
        
        self.mod_key = str(self.module_id)
        if self.mod_key not in self.scenario_state["combat_state"]:
            self.scenario_state["combat_state"][self.mod_key] = {
                "participants": [], # List of dictionaries, each representing a combatant
                "turn_idx": 0,      # Index of the participant whose turn it is
                "round": 1,         # Current combat round
                "started": False    # Flag to indicate if combat has started
            }
        
        self.storage = self.scenario_state["combat_state"][self.mod_key]

    def _get_scaled_monsters(self) -> list[dict]:
        """
        Retrieves the list of monsters appropriate for the current scenario's
        tier mode and total Challenge Points (CP).

        Returns:
            list[dict]: A list of monster dictionaries for the current scaling group.
                        Returns an empty list if no matching group is found.
        """
        cp = self.scenario_state.get("total_cp", 0)
        scaling_groups = self.module_data.get("scaling", [])
        
        for group in scaling_groups:
            if group["tier"] == self.tier_mode:
                if group["min_cp"] <= cp <= group["max_cp"]:
                    return group.get("monsters", [])
        return []

    def _handle_move(self, from_idx: int, p_id: str):
        """
        Callback to handle manual reordering of participants in the initiative tracker.
        This function is triggered when a participant's position number is changed.

        Args:
            from_idx (int): The original index of the participant in the list.
            p_id (str): The unique ID of the participant being moved.
        """
        key = f"pos_{self.module_id}_{p_id}"
        new_pos = st.session_state.get(key)
        if new_pos is None:
            return

        target_idx = new_pos - 1 # Convert 1-based UI position to 0-based list index
        if 0 <= target_idx < len(self.storage["participants"]) and target_idx != from_idx:
            # 1. Reorder the participant list by popping and inserting
            participant = self.storage["participants"].pop(from_idx)
            self.storage["participants"].insert(target_idx, participant)

            # 2. Sync Streamlit session state values for all position widgets to match new indices.
            # This is crucial to prevent the UI from showing duplicate position numbers
            # or incorrect values after a reorder.
            for i, p in enumerate(self.storage["participants"]):
                st.session_state[f"pos_{self.module_id}_{p['id']}"] = i + 1

            self.storage["turn_idx"] = 0 # Reset turn to the first participant to avoid confusion
            self.save_callback() # Persist the reordered list

    def setup_combat(self):
        """
        Initializes the combat encounter by merging player characters from the roster
        and scaled monsters into a single list of participants.
        Assigns initial initiative rolls for monsters and sets combat status to started.
        """
        roster = self.scenario_state.get("roster", [])
        monsters = self._get_scaled_monsters()
        
        new_participants = []
        
        # Add Players as participants
        for char in roster:
            name = char.get("char") or char.get("player") or "Unknown Hero"
            new_participants.append({
                "id": str(uuid.uuid4()), # Assign a unique ID to each participant
                "name": name,
                "type": "player",
                "init": 0, # Players typically input their own initiative
                "hp": 0, "max_hp": 0 # Players track their own HP outside the app
            })
            
        # Add Monsters as participants
        for m in monsters:
            hp_val = m.get("max_hp", 10)
            init_mod = m.get("init_mod", 0)
            roll = random.randint(1, 20) # Roll d20 for monster initiative
            
            new_participants.append({
                "id": str(uuid.uuid4()),
                "name": m["name"],
                "type": "monster",
                "token": "", # Placeholder for a visual token/identifier
                "ac": m.get("ac", "N/A"),
                "init": roll + init_mod, # Calculate total initiative
                "hp": hp_val, "max_hp": hp_val, # Current and max HP for monsters
                "notes": "", # Space for conditions or temporary notes
                "markdown": m.get("markdown", "") # Store monster stat block markdown
            })
            
        self.storage["participants"] = new_participants
        self.storage["started"] = True
        self.storage["turn_idx"] = 0
        self.storage["round"] = 1
        self.save_callback() # Persist the initial combat state

    @st.dialog("Monster Stats")
    def show_monster_stats(self, name: str, markdown: str):
        """
        Streamlit dialog to display a monster's full stat block in Markdown format.

        Args:
            name (str): The name of the monster.
            markdown (str): The Markdown content of the monster's stat block.
        """
        if not markdown:
            st.info(f"No stat block provided for {name}.")
            return
        st.markdown(markdown)

    def render(self):
        """
        Renders the combat encounter module in the Streamlit application.
        Provides controls to start/reset combat, advance turns, sort initiative,
        and manage individual participant's stats (HP, initiative, notes).
        """
        display_label = self.module_data.get("label") or "⚔️ Combat Encounter"
        # The expander is auto-expanded if combat has already started
        with st.expander(display_label, expanded=self.storage.get("started", False)):
            if not self.storage["started"]:
                st.info("Combat not started. Scaling will be applied based on current Roster and Tier.")
                if st.button("🎲 Roll Initiative & Start", key=f"start_{self.module_id}"):
                    self.setup_combat() # Initialize combat participants
                    st.rerun() # Rerun to display the combat tracker
                return

            # Action Bar for combat controls
            c1, c2, c3 = st.columns([2, 2, 4])
            if c1.button("⏭️ Next Turn", key=f"next_{self.module_id}", use_container_width=True):
                next_idx = self.storage["turn_idx"] + 1
                if next_idx >= len(self.storage["participants"]):
                    self.storage["turn_idx"] = 0 # Loop back to the first participant
                    self.storage["round"] = self.storage.get("round", 1) + 1 # Increment round
                else:
                    self.storage["turn_idx"] = next_idx
                self.save_callback()
                st.rerun()
                
            if c2.button("🔃 Sort Order", key=f"sort_{self.module_id}", use_container_width=True):
                # Sort participants by initiative (descending), then by type (monsters first on ties)
                self.storage["participants"].sort(key=lambda x: (x["init"], 1 if x["type"] == "monster" else 0), reverse=True)
                self.storage["turn_idx"] = 0 # Reset turn after sorting
                self.save_callback()
                st.rerun()
                
            if c3.button("🗑️ Reset Encounter", key=f"reset_{self.module_id}", use_container_width=True):
                # Reset all combat-related state variables
                self.storage["started"] = False
                self.storage["participants"] = []
                self.storage["turn_idx"] = 0
                self.storage["round"] = 1
                self.save_callback()
                st.rerun()

            # Participant Table Headers
            st.write("---")
            header = st.columns([0.7, 0.4, 1.8, 1.0, 0.7, 0.6, 0.6, 1.4, 2.3])
            header[0].caption("Pos")
            header[2].caption("Participant")
            header[3].caption("Token")
            header[4].caption("AC")
            header[5].caption("Mod")
            header[6].caption("Init")
            header[7].caption("Health")
            header[8].caption("Damage & Healing")

            # Render each participant's row
            for idx, p in enumerate(self.storage["participants"]):
                # Ensure participant has a unique ID (for backward compatibility with older saves)
                if "id" not in p:
                    p["id"] = str(uuid.uuid4())
                    self.save_callback()

                p_id = p["id"]
                is_turn = (idx == self.storage["turn_idx"])
                
                # Apply styling to highlight the current turn
                bg_color = "#e8f5e9" if is_turn else "transparent" # Light green background
                border = "2px solid #2e7d32" if is_turn else "1px solid #ddd" # Darker green border
                
                with st.container():
                    # Custom HTML for styling the row container
                    st.markdown(f"""
                        <div style="background-color: {bg_color}; border: {border}; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
                    """, unsafe_allow_html=True)
                    
                    cols = st.columns([0.7, 0.4, 1.8, 1.0, 0.7, 0.6, 0.6, 1.4, 2.3])
                    
                    # Position Control (number input for manual reordering)
                    pos_key = f"pos_{self.module_id}_{p_id}"
                    cols[0].number_input(
                        "Pos", 
                        1, len(self.storage["participants"]), 
                        value=idx + 1, # Display 1-based position
                        key=pos_key, 
                        on_change=self._handle_move, # Callback for position change
                        args=(idx, p_id), # Arguments to pass to the callback
                        label_visibility="collapsed"
                    )

                    # Turn indicator
                    if is_turn:
                        cols[1].write("▶️")
                    
                    if p["type"] == "monster":
                        # Monster Name (clickable to show stat block)
                        if cols[2].button(p['name'], key=f"ms_btn_{self.module_id}_{p_id}", use_container_width=True):
                            self.show_monster_stats(p['name'], p.get('markdown', ''))
                        
                        # Token Input
                        new_token = cols[3].text_input("Tkn", value=p.get("token", ""), key=f"tkn_{self.module_id}_{p_id}", label_visibility="collapsed")
                        if new_token != p.get("token"):
                            p["token"] = new_token
                            self.save_callback()
                        
                        # Display AC
                        cols[4].write(str(p.get("ac", "N/A")))

                        # Display Initiative Modifier (assuming 10 is base for roll)
                        cols[5].write(f"+{p.get('init', 0) - 10}") 
                        
                        # Initiative Input for Monster (allows GM to adjust)
                        new_init = cols[6].number_input("Init", value=p.get("init", 0), key=f"minit_{self.module_id}_{p_id}", label_visibility="collapsed", step=1)
                        if new_init != p.get("init"):
                            p["init"] = new_init
                            self.save_callback()
                            st.rerun()
                    else: # Player character row
                        cols[2].markdown(f"**{p['name']}**")
                        cols[3].write("-") # No token for players
                        cols[4].write("-") # No AC for players
                        cols[5].caption("Roster") # Indicate this is from the roster
                        
                        # Player Initiative Input
                        new_init = cols[6].number_input("Init", value=p.get("init", 0), key=f"init_{self.module_id}_{p_id}", label_visibility="collapsed", step=1)
                        if new_init != p.get("init"):
                            p["init"] = new_init
                            self.save_callback()
                            st.rerun()
                    
                    # Health Tracking (for Monsters Only)
                    if p["type"] == "monster":
                        max_h = p.get("max_hp", 1)
                        # Calculate health percentage for progress bar
                        health_pct = max(0, min(100, (p["hp"] / (max_h if max_h > 0 else 1)) * 100))
                        cols[7].write(f"**{p['hp']}** / {p['max_hp']}")
                        cols[7].progress(health_pct / 100) # Health bar
                        
                        # Damage/Healing Controls
                        adj_col, btn_dmg, btn_heal = cols[8].columns([2, 1, 1])
                        adj = adj_col.number_input("Adj", min_value=0, step=1, key=f"adj_{self.module_id}_{p_id}", label_visibility="collapsed")
                        
                        if btn_dmg.button("💥", key=f"dmg_{self.module_id}_{p_id}", help="Apply Damage"):
                            p["hp"] = max(0, p["hp"] - adj) # Ensure HP doesn't go below 0
                            self.save_callback()
                            st.rerun()
                            
                        if btn_heal.button("💚", key=f"heal_{self.module_id}_{p_id}", help="Apply Healing"):
                            p["hp"] = min(p["max_hp"], p["hp"] + adj) # Ensure HP doesn't exceed max_hp
                            self.save_callback()
                            st.rerun()
                    else: # For players, indicate HP is tracked externally
                        cols[7].write("-")
                        cols[8].write("*(Player tracks HP)*")

                    # Conditions / Notes section for monsters
                    if p["type"] == "monster":
                        new_notes = st.text_input("Conditions / Notes", value=p.get("notes", ""), key=f"notes_{self.module_id}_{p_id}", placeholder="e.g., Frightened 1, Prone, Persistent Fire 1d6")
                        if new_notes != p.get("notes"):
                            p["notes"] = new_notes
                            self.save_callback()
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True) # Close custom HTML div

            st.write("---")
            # Display current round and tier mode
            round_num = self.storage.get("round", 1)
            st.caption(f"Active Round: {round_num} | Scale: {self.tier_mode} Tier")