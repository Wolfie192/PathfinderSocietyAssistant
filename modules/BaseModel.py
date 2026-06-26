class BaseModel:
    """
    The base model for all Streamlit modules in the application.
    All interactive components or display elements that can be added to a scenario page
    should inherit from this class.
    """
    def __init__(self):
        """
        Initializes the base model. Subclasses should call super().__init__()
        and then initialize their specific attributes.
        """
        pass

    def render(self):
        """
        Abstract method to render the module's content using Streamlit components.
        Each concrete module inheriting from BaseModel must implement this method
        to define how it displays itself in the Streamlit application.
        """
        pass