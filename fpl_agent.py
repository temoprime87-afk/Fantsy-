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


# 6. Player analysis
print("\n=== PLAYER ANALYSIS ===")

valid_players = [
    p for p in players
    if p.get("minutes", 0) > 0
]

top_points = sorted(
    valid_players,
    key=lambda p: p.get("total_points", 0),
    reverse=True
)[:10]

print("\nTop 10 by total points:")

for i, player in enumerate(top_points, 1):
    print(
        i,
        player.get("web_name"),
        "| Points:", player.get("total_points", 0),
        "| Form:", player.get("form", 0),
        "| Minutes:", player.get("minutes", 0),
        "| Price:", player.get("now_cost", 0) / 10
    )


top_form = sorted(
    valid_players,
    key=lambda p: float(p.get("form", 0) or 0),
    reverse=True
)[:10]

print("\nTop 10 by form:")

for i, player in enumerate(top_form, 1):
    print(
        i,
        player.get("web_name"),
        "| Form:", player.get("form", 0),
        "| Points:", player.get("total_points", 0),
        "| Minutes:", player.get("minutes", 0),
        "| Price:", player.get("now_cost", 0) / 10
    )


# 7. Fixture analysis
print("\n=== FIXTURE ANALYSIS ===")

team_names = {
    t["id"]: t["name"]
    for t in teams
}

team_fixtures = {
    t["id"]: []
    for t in teams
}

future_fixtures = [
    f for f in fixtures
    if f.get("event") is not None
    and f.get("event") >= current_event
]

for fixture in future_fixtures:
    home_id = fixture.get("team_h")
    away_id = fixture.get("team_a")

    if home_id in team_fixtures:
        team_fixtures[home_id].append({
            "gameweek": fixture.get("event"),
            "opponent": team_names.get(away_id, "Unknown"),
            "home": True,
            "difficulty": fixture.get("team_h_difficulty")
        })

    if away_id in team_fixtures:
        team_fixtures[away_id].append({
            "gameweek": fixture.get("event"),
            "opponent": team_names.get(home_id, "Unknown"),
            "home": False,
            "difficulty": fixture.get("team_a_difficulty")
        })


print("\nNext fixtures by team:")

for team_id, team_name in team_names.items():

    upcoming = sorted(
        team_fixtures.get(team_id, []),
        key=lambda x: x["gameweek"]
    )[:5]

    if not upcoming:
        continue

    print("\n", team_name)

    for fixture in upcoming:
        venue = "H" if fixture["home"] else "A"

        print(
            "GW",
            fixture["gameweek"],
            venue,
            "vs",
            fixture["opponent"],
            "| Difficulty:",
            fixture["difficulty"]
        )


# 8. Save all data
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

print("\nFPL data saved to fpl_data.json")
print("Agent connected successfully.")
