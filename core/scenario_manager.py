import json
import logging # Import the logging module

from pathlib import Path
from core.scenario_data import ScenarioData  # Import the new ScenarioData class

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScenarioManager:
    """
    Class for managing scenario data and save states as the scenario is being run.
    Manages scenario data and save states as modules are added, modified, and/or deleted.
    This class now focuses purely on data management and business logic,
    with UI rendering concerns moved to ui/scenario_runner_ui.py and ui/scenario_editor_ui.py.
    """

    def __init__(self, season: str, scenario: str, root_dir: Path):
        # Define and create scenario-specific directories
        self.scenario_dir = root_dir / "data" / season / scenario
        self.scenario_dir.mkdir(parents=True, exist_ok=True)

        self.image_dir = self.scenario_dir / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

        self.monster_dir = self.scenario_dir / "monsters" # This is for scenario-specific monsters, not global
        self.monster_dir.mkdir(parents=True, exist_ok=True)

        # Store season and scenario identifiers
        self.season: str = season
        self.scenario: str = scenario

        # Retrieve scenario details using ScenarioData class for better encapsulation
        # Provide default values in case ScenarioData methods return None
        self.name: str = ScenarioData.get_scenario_name(self.season, self.scenario) or "Unknown Scenario"
        self.tier_min: int = ScenarioData.get_scenario_tier_min(self.season, self.scenario) or 1
        self.tier_max: int = ScenarioData.get_scenario_tier_max(self.season, self.scenario) or 1

        # Initialize scenario data structure with a default main page
        self.scenario_data: dict = {"pages": [{"label": "Main Page", "modules": []}]}
        self.scenario_state: dict = {}  # Stores dynamic state during scenario play

        self.root_dir = root_dir  # Store root_dir for passing to modules

        self.load()  # Load existing scenario data and state

    def load(self):
        """
        Method for loading the scenario_data and scenario_state when the scenario is selected.
        It attempts to load from JSON files; if not found or corrupted, it initializes defaults.
        """
        scenario_data_path = self.scenario_dir / "scenario_data.json"
        scenario_state_path = self.scenario_dir / "scenario_state.json"

        # Reset scenario_data to default before loading to ensure a clean state if loading fails
        self.scenario_data = {"pages": [{"label": "Main Page", "modules": []}]}

        if scenario_data_path.exists():
            with open(scenario_data_path, "r", encoding="utf-8") as f:
                try:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        # Handle legacy format where modules were directly under the root
                        if "modules" in loaded_data and "pages" not in loaded_data:
                            self.scenario_data["pages"] = [
                                {"label": "Main Page", "modules": loaded_data["modules"]}
                            ]
                        else:
                            self.scenario_data.update(loaded_data)
                except json.JSONDecodeError:
                    logger.warning(f"Scenario data file '{scenario_data_path}' is malformed. Using default data.")
                except Exception as e:
                    logger.error(f"An unexpected error occurred loading scenario data from '{scenario_data_path}': {e}")

        if scenario_state_path.exists():
            with open(scenario_state_path, "r", encoding="utf-8") as f:
                try:
                    self.scenario_state = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Scenario state file '{scenario_state_path}' is malformed. Initializing empty state.")
                    self.scenario_state = {}
                except Exception as e:
                    logger.error(f"An unexpected error occurred loading scenario state from '{scenario_state_path}': {e}")
        else:
            # Initialize empty state if no state file exists
            logger.info(f"Scenario state file '{scenario_state_path}' not found. Initializing empty state.")
            self.scenario_state = {}

    def reset(self):
        """
        Method for resetting the scenario_state.
        Wipes all dynamic data like character rosters and combat states.
        """
        self.scenario_state = {}
        self.save()  # Persist the reset state
        logger.info(f"Scenario state for '{self.season}/{self.scenario}' has been reset.")


    def _module_save_callback(self):
        """
        Callback for modules to save their internal state and clear any dangling edit dialogs.
        This is called by individual modules when they make changes that need to be persisted.
        """
        self.save()
        logger.debug(f"Module save callback triggered for '{self.season}/{self.scenario}'.")


    def save(self):
        """
        Method for saving the scenario_data and scenario_state when modifications are made.
        Writes the current scenario data and state to respective JSON files.
        """
        scenario_data_path = self.scenario_dir / "scenario_data.json"
        scenario_state_path = self.scenario_dir / "scenario_state.json"

        try:
            with open(scenario_data_path, "w", encoding="utf-8") as f:
                json.dump(self.scenario_data, f, indent=4)
            logger.info(f"Scenario data saved to '{scenario_data_path}'.")
        except IOError as e:
            logger.error(f"Failed to save scenario data to '{scenario_data_path}': {e}")

        try:
            with open(scenario_state_path, "w", encoding="utf-8") as f:
                json.dump(self.scenario_state, f, indent=4)
            logger.info(f"Scenario state saved to '{scenario_state_path}'.")
        except IOError as e:
            logger.error(f"Failed to save scenario state to '{scenario_state_path}': {e}")