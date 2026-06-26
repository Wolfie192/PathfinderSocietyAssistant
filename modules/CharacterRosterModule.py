from modules.BaseModel import BaseModel
import streamlit as st

class CharacterRosterModule(BaseModel):
    """
    Module for managing a dynamic roster of 2-6 characters within a scenario.
    It allows GMs to add, edit, and remove characters, and automatically calculates
    Challenge Points (CP) based on character levels relative to the scenario's tier.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, scenario_state: dict, tier_min: int, tier_max: int, save_callback):
        """
        Initializes the CharacterRosterModule.

        Args:
            scenario_state (dict): The global state of the current scenario, used for storing
                                   and retrieving the character roster.
            tier_min (int): The minimum tier level for the current scenario.
            tier_max (int): The maximum tier level for the current scenario.
            save_callback (callable): A function to call when the module's state changes
                                      and needs to be persisted to the scenario_state.
        """
        super().__init__()
        self.scenario_state = scenario_state
        self.tier_min = tier_min
        self.tier_max = tier_max
        self.save_callback = save_callback

        # Initialize roster in scenario_state if it doesn't exist.
        # Starts with a minimum of two character slots.
        if "roster" not in self.scenario_state:
            self.scenario_state["roster"] = [
                {"player": "", "char": "", "level": self.tier_min, "perception": 0},
                {"player": "", "char": "", "level": self.tier_min, "perception": 0}
            ]

    def render(self):
        """
        Renders the character roster management interface in the Streamlit application.
        Displays input fields for each character, their calculated CP, and controls
        to add or remove characters.
        """
        st.subheader("👥 Character Roster")
        roster = self.scenario_state["roster"]
        updated_roster = [] # Buffer to hold changes before committing to state

        # Define column headers for the roster table
        h1, h2, h3, h4, h5, h6 = st.columns([2.5, 2.5, 1.2, 1.5, 1.5, 0.8])
        h1.caption("Player Name")
        h2.caption("Character Name")
        h3.caption("Level")
        h4.caption("Perception")
        h5.caption("CP")
        h6.write("") # Empty column for the delete button

        # Iterate through each character in the roster to display their row
        for i, char in enumerate(roster):
            with st.container(): # Use a container to group elements for each character row
                c1, c2, c3, c4, c5, c6 = st.columns([2.5, 2.5, 1.2, 1.5, 1.5, 0.8])
                
                # Input fields for Player Name, Character Name, Level, and Perception
                p_val = c1.text_input("Player", char.get("player", ""), key=f"p_{i}", label_visibility="collapsed")
                c_val = c2.text_input("Char", char.get("char", ""), key=f"c_{i}", label_visibility="collapsed")
                l_val = c3.number_input("Lvl", self.tier_min, self.tier_max, char.get("level", self.tier_min), key=f"l_{i}", label_visibility="collapsed")
                perc_val = c4.number_input("Perc", value=char.get("perception", 0), key=f"perc_{i}", label_visibility="collapsed")
                
                # Calculate Challenge Points (CP) based on character level and scenario's min tier
                # CP mapping: Min tier level = 2 CP, +1 level = 3 CP, +2 levels = 4 CP, +3 levels = 6 CP
                diff = l_val - self.tier_min
                cp = {0: 2, 1: 3, 2: 4, 3: 6}.get(diff, 0)
                
                # Display CP. Using markdown with inline CSS for consistent styling and vertical alignment.
                c5.markdown(f"""
                    <div style="height: 38px; display: flex; align-items: center; border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 4px; padding: 0 10px; background-color: rgba(240, 242, 246, 0.5);">
                        {cp}
                    </div>
                """, unsafe_allow_html=True)
                
                # Delete button for character rows. Only visible if there are more than 2 characters.
                if len(roster) > 2:
                    if c6.button("🗑️", key=f"del_char_{i}", help="Remove Character"):
                        self.scenario_state["roster"].pop(i) # Remove character from the roster
                        self.save_callback() # Trigger save to persist changes
                        st.rerun() # Rerun the app to update the UI
                
                # Add current character's updated data to the buffer
                updated_roster.append({
                    "player": p_val, 
                    "char": c_val, 
                    "level": l_val, 
                    "perception": perc_val
                })

        # Check if the roster has changed and, if so, update the scenario state and save
        if updated_roster != roster:
            self.scenario_state["roster"] = updated_roster
            self.save_callback()
            st.rerun()

        # Button to add a new character. Limited to a maximum of 6 characters.
        if len(updated_roster) < 6:
            if st.button("➕ Add Character"):
                # Append a new character with default values
                self.scenario_state["roster"].append({"player": "", "char": "", "level": self.tier_min, "perception": 0})
                self.save_callback() # Trigger save to persist changes
                st.rerun() # Rerun the app to display the new character row
        
        st.divider() # Visual separator at the end of the module