from modules.BaseModel import BaseModel
import streamlit as st

class TextModule(BaseModel):
    """
    Module for displaying markdown formatted text within a scenario page.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, content: str):
        """
        Initializes the TextModule with the given markdown content.

        Args:
            content (str): The markdown string to be displayed.
        """
        super().__init__()
        self.content = content

    def render(self):
        """
        Renders the markdown content using Streamlit's markdown component.
        If the content is empty, it displays an informational message.
        """
        if not self.content:
            st.info("Empty text module.")
            return
        st.markdown(self.content)