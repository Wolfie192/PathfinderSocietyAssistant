import re

def parse_scribe_markdown(md_text: str):
    """
    Parses Pathfinder Scribe markdown for monster Name, HP, AC, and Initiative.
    """
    # Regex to extract Name (text after first '#')
    name_match = re.search(r"^#\s*(.*)", md_text, re.MULTILINE)
    # Regex to extract AC (number after **AC**)
    ac_match = re.search(r"\*\*AC\*\*\s*(\d+)", md_text)
    # Regex to extract HP (number after **HP**)
    hp_match = re.search(r"\*\*HP\*\*\s*(\d+)", md_text)
    # Regex to extract Initiative (first modifier (+/- X) after traits line)
    init_match = re.search(r"- ;.*?\n\*\*.*?\*\*\s*([+-]\d+)", md_text, re.DOTALL)

    return {
        "name": name_match.group(1).strip() if name_match else "Unknown Monster",
        "ac": ac_match.group(1) if ac_match else "N/A",
        "hp": int(hp_match.group(1)) if hp_match else 10,
        "init": int(init_match.group(1)) if init_match else 0,
        "markdown": md_text # Store the original markdown as well
    }