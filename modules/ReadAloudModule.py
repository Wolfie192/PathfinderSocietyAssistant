from modules.BaseModel import BaseModel
import re
import streamlit as st

class ReadAloudModule(BaseModel):
    """
    Module for displaying narrative text intended to be read aloud by the GM.
    The text is presented within a styled box with a border and dark green text
    to visually distinguish it from other content.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, content: str):
        """
        Initializes the ReadAloudModule with the narrative content.

        Args:
            content (str): The text content to be displayed as read-aloud.
        """
        super().__init__()
        self.content = content

    def render(self):
        """
        Renders the read-aloud content in the Streamlit application.
        The content is processed to handle paragraphs and then displayed within
        a custom-styled HTML div using st.markdown with unsafe_allow_html=True.
        """
        if not self.content:
            st.info("Empty read aloud module.")
            return

        # Split content into paragraphs, handling multiple newlines as paragraph breaks
        paragraphs = re.split(r'\n{2,}', self.content)

        processed_paragraphs = []
        for para in paragraphs:
            # Replace single newlines within a paragraph with spaces for better flow
            processed_para = re.sub(r'\n', ' ', para.strip())
            processed_paragraphs.append(processed_para)

        # Join processed paragraphs back with double newlines for HTML rendering
        cleaned_content = '\n\n'.join(processed_paragraphs)

        # Render the content within a styled div
        st.markdown(
            f'<div style="color: #1b5e20; background-color: #f1f8e9; border-left: 5px solid #2e7d32; padding: 15px; font-size: 1.1em; font-style: italic; white-space: pre-wrap; border-radius: 4px;">{cleaned_content}</div>',
            unsafe_allow_html=True
        )