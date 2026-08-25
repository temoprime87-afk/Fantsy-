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


print("=== FPL AGENT ===")

# 1. Team data
team = get_json(
    f"https://fantasy.premierleague.com/api/entry/{TEAM_ID}/"
)

print("Team:", team.get("name"))
print("Manager:", team.get("player_first_name"), team.get("player_last_name"))
print("Overall rank:", team.get("summary_overall_rank"))
print("Total points:", team.get("summary_overall_points"))
print("Team value:", team.get("last_deadline_value"))

# 2. All players + gameweek data
bootstrap = get_json(
    "https://fantasy.premierleague.com/api/bootstrap-static/"
)

players = bootstrap.get("elements", [])
events = bootstrap.get("events", [])

print("Players loaded:", len(players))
print("Gameweeks loaded:", len(events))

# 3. Fixtures
fixtures = get_json(
    "https://fantasy.premierleague.com/api/fixtures/"
)

print("Fixtures loaded:", len(fixtures))

# 4. Current Gameweek
current_event = team.get("current_event")

print("Current Gameweek:", current_event)

# 5. Current team picks
if current_event:
    picks = get_json(
        f"https://fantasy.premierleague.com/api/entry/{TEAM_ID}/event/{current_event}/picks/"
    )

    print("Current squad picks loaded:", len(picks.get("picks", [])))
else:
    print("Current squad picks: not available yet")

print("\nAgent connected successfully.")
