from modules.BaseModel import BaseModel
import streamlit as st
from pathlib import Path

class ImageModule(BaseModel):
    """
    Module for displaying images within a scenario page.
    Inherits from BaseModel to integrate with the scenario management system.
    """
    def __init__(self, image_dir: Path, image_name: str, width: int | None = None):
        """
        Initializes the ImageModule with the directory where images are stored,
        the name of the image file, and an optional display width.

        Args:
            image_dir (Path): The absolute path to the directory containing the image.
            image_name (str): The filename of the image to be displayed.
            width (int | None): Optional. The width to display the image in pixels.
                                If None, Streamlit will determine the width automatically.
        """
        super().__init__()
        self.image_dir = image_dir
        self.image_name = image_name
        self.width = width

    def render(self):
        """
        Renders the image in the Streamlit application.
        It constructs the full path to the image and displays it using st.image.
        Includes error handling for cases where the image file is not specified or not found.
        """
        if not self.image_name:
            st.warning("No image file specified for this module.")
            return

        img_path = self.image_dir / self.image_name
        if img_path.exists():
            # Ensure width is an integer, providing a default if it's None
            display_width = self.width if self.width is not None else 700
            st.image(str(img_path), width=display_width)
        else:
            st.error(f"Image not found at expected path: {img_path}")