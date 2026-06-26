from core.scenarios import SCENARIOS

class ScenarioData:
    """
    Encapsulates access to scenario data, providing methods to retrieve
    seasons and scenarios.
    """

    @staticmethod
    def get_available_seasons() -> list[str]:
        """
        Returns a list of available season keys.
        """
        return list(SCENARIOS.keys())

    @staticmethod
    def get_scenarios_for_season(season_key: str) -> dict:
        """
        Returns a dictionary of scenarios for a given season key.
        Returns an empty dictionary if the season key is not found.
        """
        return SCENARIOS.get(season_key, {})

    @staticmethod
    def get_scenario_name(season_key: str, scenario_key: str) -> str | None:
        """
        Returns the name of a specific scenario.
        Returns None if the season or scenario key is not found.
        """
        season_scenarios = ScenarioData.get_scenarios_for_season(season_key)
        return season_scenarios.get(scenario_key, {}).get("name")

    @staticmethod
    def get_scenario_tier_min(season_key: str, scenario_key: str) -> int | None:
        """
        Returns the minimum tier of a specific scenario.
        Returns None if the season or scenario key is not found.
        """
        season_scenarios = ScenarioData.get_scenarios_for_season(season_key)
        return season_scenarios.get(scenario_key, {}).get("tier_min")

    @staticmethod
    def get_scenario_tier_max(season_key: str, scenario_key: str) -> int | None:
        """
        Returns the maximum tier of a specific scenario.
        Returns None if the season or scenario key is not found.
        """
        season_scenarios = ScenarioData.get_scenarios_for_season(season_key)
        return season_scenarios.get(scenario_key, {}).get("tier_max")