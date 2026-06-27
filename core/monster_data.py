import json
from pathlib import Path
import logging # Import the logging module
import re # Import re for sanitization

from core.utils import parse_scribe_markdown

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_global_monster_dir(root_dir: Path) -> Path:
    """Helper to get the path to the global monsters directory."""
    monster_dir = root_dir / "data" / "monsters"
    monster_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists
    return monster_dir

def _sanitize_filename(name: str) -> str:
    """Sanitizes a string to be used as a filename."""
    # Replace any non-alphanumeric, non-space, non-underscore, non-dot characters with nothing
    filename = re.sub(r'[^\w\s.-]', '', name)
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    # Remove leading/trailing underscores or dots
    filename = filename.strip('_.')
    return filename + ".json"

def load_all_global_monsters(root_dir: Path) -> list[dict]:
    """Loads all global monster data from JSON files."""
    monster_dir = get_global_monster_dir(root_dir)
    monsters = []
    for monster_file in monster_dir.glob("*.json"):
        try:
            with open(monster_file, "r", encoding="utf-8") as f:
                monster_data = json.load(f)
                monster_data["_filename"] = monster_file.name # Store filename for edit/delete
                monsters.append(monster_data)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not load monster from {monster_file.name}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred loading monster {monster_file.name}: {e}")
    # Sort monsters alphabetically by name
    monsters.sort(key=lambda x: x.get("name", "Unknown Monster").lower())
    return monsters

def save_global_monster(root_dir: Path, monster_markdown: str):
    """Parses markdown and saves a new global monster to a JSON file."""
    monster_dir = get_global_monster_dir(root_dir)
    monster_data = parse_scribe_markdown(monster_markdown)
    monster_name = monster_data["name"]

    filename = _sanitize_filename(monster_name)
    file_path = monster_dir / filename # Moved assignment outside try block

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(monster_data, f, indent=4)
        logger.info(f"Monster '{monster_name}' saved to {file_path}")
        return monster_name
    except IOError as e:
        logger.error(f"Failed to save monster '{monster_name}' to {file_path}: {e}")
        raise # Re-raise to be handled by the UI layer

def update_global_monster(root_dir: Path, original_filename: str, edited_markdown: str):
    """Updates an existing global monster's data and potentially its filename."""
    monster_dir = get_global_monster_dir(root_dir)
    updated_monster_data = parse_scribe_markdown(edited_markdown)
    updated_monster_name = updated_monster_data["name"]

    new_filename = _sanitize_filename(updated_monster_name)
    file_path = monster_dir / new_filename # Moved assignment outside try block

    try:
        # If filename changed, delete old file
        if new_filename != original_filename:
            old_file_path = monster_dir / original_filename
            if old_file_path.exists():
                old_file_path.unlink() # Use Path.unlink() instead of os.remove()
                logger.info(f"Deleted old monster file: {original_filename}")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated_monster_data, f, indent=4)
        logger.info(f"Monster '{updated_monster_name}' updated and saved to {file_path}")
        return updated_monster_name
    except IOError as e:
        logger.error(f"Failed to update monster '{updated_monster_name}' to {file_path}: {e}")
        raise # Re-raise to be handled by the UI layer

def delete_global_monster(root_dir: Path, filename: str):
    """Deletes a global monster JSON file."""
    monster_dir = get_global_monster_dir(root_dir)
    file_path = monster_dir / filename
    if file_path.exists():
        try:
            file_path.unlink() # Use Path.unlink() instead of os.remove()
            logger.info(f"Monster file '{filename}' deleted successfully.")
            return True
        except OSError as e:
            logger.error(f"Failed to delete monster file '{filename}': {e}")
            return False
    logger.warning(f"Attempted to delete non-existent monster file: {filename}")
    return False