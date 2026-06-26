from modules.BaseModel import BaseModel
import streamlit as st


class LineBreakModule(BaseModel):
    """
    Module for displaying a customizable colored horizontal line break within a scenario page.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, color: str):
        """
        Initializes the LineBreakModule with a specified color for the line.

        Args:
            color (str): The CSS color value for the line (e.g., "#2e7d32", "red", "rgb(0,0,0)").
        """
        super().__init__()
        self.color = color

    def render(self):
        """
        Renders a colored horizontal line using Streamlit's markdown component with unsafe HTML.
        The line is styled to be a thick, rounded separator.
        """
        st.markdown(
            f'<hr style="border: none; border-top: 10px solid {self.color}; border-radius: 5px;">',
            unsafe_allow_html=True
        )