import json
import urllib.request

TEAM_ID = 9623737

def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

team = get_json(
    f"https://fantasy.premierleague.com/api/entry/{TEAM_ID}/"
)

print("=== FPL AGENT ===")
print("Team:", team.get("name"))
print("Manager:", team.get("player_first_name"), team.get("player_last_name"))
print("Overall rank:", team.get("summary_overall_rank"))
print("Total points:", team.get("summary_overall_points"))
print("Team value:", team.get("last_deadline_value"))

print("\nAgent connected successfully.")
