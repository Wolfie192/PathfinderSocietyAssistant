from pathlib import Path
from core.scenario_data import ScenarioData # Import the new ScenarioData class


def verify_directories(root_dir: Path):
    """
    Ensures the main data directory and all season subdirectories exist.
    This function creates them if they do not already exist.
    """
    # Define the path to the main data directory
    data_dir = root_dir / "data"
    # Create the data directory if it doesn't exist, including any necessary parent directories
    data_dir.mkdir(parents=True, exist_ok=True)

    # Iterate through all available seasons using the ScenarioData class
    for season in ScenarioData.get_available_seasons():
        # Create a subdirectory for each season within the data directory
        (data_dir / season).mkdir(parents=True, exist_ok=True)