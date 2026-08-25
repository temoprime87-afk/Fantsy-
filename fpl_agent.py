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
print(
    "Manager:",
    team.get("player_first_name"),
    team.get("player_last_name")
)
print("Overall rank:", team.get("summary_overall_rank"))
print("Total points:", team.get("summary_overall_points"))
print("Team value:", team.get("last_deadline_value"))

# 2. FPL database
bootstrap = get_json(
    "https://fantasy.premierleague.com/api/bootstrap-static/"
)

players = bootstrap.get("elements", [])
events = bootstrap.get("events", [])
teams = bootstrap.get("teams", [])

print("Players loaded:", len(players))
print("Gameweeks loaded:", len(events))
print("FPL teams loaded:", len(teams))

# 3. Fixtures
fixtures = get_json(
    "https://fantasy.premierleague.com/api/fixtures/"
)

print("Fixtures loaded:", len(fixtures))

# 4. Current Gameweek
current_event = team.get("current_event")

print("Current Gameweek:", current_event)

# 5. Current team picks
picks = None

if current_event:
    try:
        picks = get_json(
            f"https://fantasy.premierleague.com/api/entry/{TEAM_ID}/event/{current_event}/picks/"
        )

        print(
            "Current squad picks loaded:",
            len(picks.get("picks", []))
        )

    except Exception as e:
        print(
            "Current squad picks not available:",
            e
        )
else:
    print("Current squad picks: not available yet")


# 6. Save collected data
data = {
    "team": team,
    "players": players,
    "gameweeks": events,
    "fpl_teams": teams,
    "fixtures": fixtures,
    "current_gameweek": current_event,
    "current_picks": picks
}

with open("fpl_data.json", "w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

print("FPL data saved to fpl_data.json")
print("\nAgent connected successfully.")
