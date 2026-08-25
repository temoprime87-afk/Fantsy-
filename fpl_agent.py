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


# 6. Team names
team_names = {
    t["id"]: t["name"]
    for t in teams
}

# 7. Build upcoming fixture difficulty
team_fixtures = {
    t["id"]: []
    for t in teams
}

if current_event:
    future_fixtures = [
        f for f in fixtures
        if f.get("event") is not None
        and f.get("event") >= current_event
    ]
else:
    future_fixtures = fixtures


for fixture in future_fixtures:

    home_id = fixture.get("team_h")
    away_id = fixture.get("team_a")

    if home_id in team_fixtures:
        team_fixtures[home_id].append(
            fixture.get("team_h_difficulty", 3)
        )

    if away_id in team_fixtures:
        team_fixtures[away_id].append(
            fixture.get("team_a_difficulty", 3)
        )


# 8. Calculate fixture score
def fixture_score(player):

    team_id = player.get("team")

    difficulties = team_fixtures.get(team_id, [])

    if not difficulties:
        return 5.0

    next_fixtures = difficulties[:5]

    average_difficulty = (
        sum(next_fixtures) / len(next_fixtures)
    )

    # FPL difficulty is roughly 1-5.
    # Lower difficulty = better fixture.
    score = 10 - (average_difficulty * 2)

    return max(0, min(10, score))


# 9. Calculate player score
def player_score(player):

    form = float(player.get("form", 0) or 0)

    total_points = float(
        player.get("total_points", 0) or 0
    )

    minutes = float(
        player.get("minutes", 0) or 0
    )

    price = float(
        player.get("now_cost", 0) or 0
    ) / 10

    fixture = fixture_score(player)

    # Minutes reliability: 90+ minutes gets full score.
    minutes_score = min(minutes / 90, 10)

    # Normalize total points.
    points_score = min(total_points / 20, 10)

    # Form is already roughly on a 0-10 scale.
    form_score = min(form, 10)

    # Cheaper players receive a small value bonus.
    if price > 0:
        value_score = min(
            total_points / price,
            10
        )
    else:
        value_score = 0

    score = (
        form_score * 0.30
        + points_score * 0.25
        + minutes_score * 0.15
        + fixture * 0.20
        + value_score * 0.10
    )

    return round(score, 2)


# 10. Analyze players
print("\n=== PLAYER SCORE ANALYSIS ===")

valid_players = [
    p for p in players
    if p.get("minutes", 0) > 0
]

for player in valid_players:
    player["agent_score"] = player_score(player)


top_players = sorted(
    valid_players,
    key=lambda p: p.get("agent_score", 0),
    reverse=True
)[:20]


print("\nTop 20 players by Agent Score:")

for i, player in enumerate(top_players, 1):

    print(
        i,
        player.get("web_name"),
        "| Score:",
        player.get("agent_score"),
        "| Form:",
        player.get("form", 0),
        "| Points:",
        player.get("total_points", 0),
        "| Minutes:",
        player.get("minutes", 0),
        "| Price:",
        player.get("now_cost", 0) / 10,
        "| Fixture:",
        round(fixture_score(player), 2)
    )


# 11. Save data
data = {
    "team": team,
    "players": players,
    "gameweeks": events,
    "fpl_teams": teams,
    "fixtures": fixtures,
    "current_gameweek": current_event,
    "current_picks": picks,
    "top_players": [
        {
            "id": p.get("id"),
            "name": p.get("web_name"),
            "position": p.get("element_type"),
            "team": p.get("team"),
            "price": p.get("now_cost", 0) / 10,
            "form": p.get("form", 0),
            "total_points": p.get("total_points", 0),
            "minutes": p.get("minutes", 0),
            "agent_score": p.get("agent_score", 0)
        }
        for p in top_players
    ]
}

with open("fpl_data.json", "w", encoding="utf-8") as file:
    json.dump(
        data,
        file,
        ensure_ascii=False,
        indent=2
    )

print("\nFPL data saved to fpl_data.json")
print("Agent connected successfully.")
