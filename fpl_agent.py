import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

TEAM_ID = 9623737

BASE_URL = "https://fantasy.premierleague.com/api"

USER_AGENT = "Mozilla/5.0 FPL-Autonomous-Agent"

TOP_PLAYERS = 30
UPCOMING_FIXTURES = 5


# ============================================================
# API
# ============================================================

def get_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)

    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"HTTP {error.code}: {error.reason} - {url}"
        )

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Network error: {error.reason} - {url}"
        )


# ============================================================
# SAFE HELPERS
# ============================================================

def number(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


# ============================================================
# CURRENT EVENT / SQUAD HELPERS
# ============================================================

def find_current_gameweek(events, team):
    # Prefer the official bootstrap event flags.
    for event in events:
        if event.get("is_current"):
            return event.get("id")

    # Then use the team's current_event if available.
    team_event = team.get("current_event")
    if team_event is not None:
        return integer(team_event, None)

    # Finally use the latest finished event.
    finished = [
        event.get("id")
        for event in events
        if event.get("finished")
        and event.get("id") is not None
    ]

    return max(finished) if finished else None


def load_current_squad(team_id, current_event, events):
    """
    Try the current GW first, then the latest completed GW.
    Some FPL API states return 404 when picks for a GW are not
    published/available yet. A 404 is therefore treated as a
    normal unavailable-data condition, not as an agent failure.
    """

    candidates = []

    if current_event is not None:
        candidates.append(current_event)

    completed_events = sorted(
        [
            integer(event.get("id"), None)
            for event in events
            if event.get("finished")
            and event.get("id") is not None
        ],
        reverse=True
    )

    for event_id in completed_events:
        if event_id is not None and event_id not in candidates:
            candidates.append(event_id)

    for event_id in candidates[:6]:
        url = (
            f"{BASE_URL}/entry/"
            f"{team_id}/event/"
            f"{event_id}/picks/"
        )

        try:
            data = get_json(url)
            picks = data.get("picks", [])

            if picks:
                return {
                    "data": data,
                    "gameweek": event_id,
                    "source": url
                }

        except Exception as error:
            print(
                f"Squad GW{event_id} unavailable: {error}"
            )

    return None


# ============================================================
# START
# ============================================================

print("====================================")
print("       FPL AUTONOMOUS AGENT")
print("====================================")
print("")


# ============================================================
# 1. TEAM
# ============================================================

print("Loading team data...")

team = get_json(
    f"{BASE_URL}/entry/{TEAM_ID}/"
)

print("Team:", team.get("name"))

print(
    "Manager:",
    team.get("player_first_name"),
    team.get("player_last_name")
)

print(
    "Overall rank:",
    team.get("summary_overall_rank")
)

print(
    "Total points:",
    team.get("summary_overall_points")
)

print(
    "Team value:",
    team.get("last_deadline_value")
)


# ============================================================
# 2. BOOTSTRAP
# ============================================================

print("")
print("Loading FPL database...")

bootstrap = get_json(
    f"{BASE_URL}/bootstrap-static/"
)

players = bootstrap.get("elements", [])
events = bootstrap.get("events", [])
teams = bootstrap.get("teams", [])

print("Players loaded:", len(players))
print("Gameweeks loaded:", len(events))
print("FPL teams loaded:", len(teams))


# ============================================================
# 3. FIXTURES
# ============================================================

print("")
print("Loading fixtures...")

fixtures = get_json(
    f"{BASE_URL}/fixtures/"
)

print("Fixtures loaded:", len(fixtures))


# ============================================================
# 4. CURRENT GAMEWEEK
# ============================================================

current_event = find_current_gameweek(
    events,
    team
)

print("")
print("Current Gameweek:", current_event)


# ============================================================
# 5. TEAM LOOKUP
# ============================================================

team_lookup = {}

for fpl_team in teams:
    team_lookup[fpl_team["id"]] = fpl_team


# ============================================================
# 6. POSITION LOOKUP
# ============================================================

positions = {
    1: "GK",
    2: "DEF",
    3: "MID",
    4: "FWD"
}


# ============================================================
# 7. FIXTURE MAP
# ============================================================

fixture_map = {}

for fixture in fixtures:
    event = fixture.get("event")

    if event is None:
        continue

    home_team = fixture.get("team_h")
    away_team = fixture.get("team_a")

    home_difficulty = fixture.get("team_h_difficulty")
    away_difficulty = fixture.get("team_a_difficulty")

    fixture_map.setdefault(home_team, []).append({
        "event": event,
        "opponent": away_team,
        "home": True,
        "difficulty": home_difficulty,
        "finished": fixture.get("finished", False),
        "kickoff": fixture.get("kickoff_time")
    })

    fixture_map.setdefault(away_team, []).append({
        "event": event,
        "opponent": home_team,
        "home": False,
        "difficulty": away_difficulty,
        "finished": fixture.get("finished", False),
        "kickoff": fixture.get("kickoff_time")
    })


# ============================================================
# 8. CURRENT SQUAD
# ============================================================

print("")
print("Loading current squad...")

squad_result = load_current_squad(
    TEAM_ID,
    current_event,
    events
)

current_picks = None
squad_gameweek = None
squad_source = None

if squad_result:
    current_picks = squad_result["data"]
    squad_gameweek = squad_result["gameweek"]
    squad_source = squad_result["source"]

    print(
        "Current squad picks loaded:",
        len(current_picks.get("picks", []))
    )

    print(
        "Squad data Gameweek:",
        squad_gameweek
    )

else:
    print(
        "Current squad picks unavailable."
    )

    print(
        "Continuing safely without squad-specific transfers."
    )


# ============================================================
# 9. PLAYER ANALYSIS
# ============================================================

analysed_players = []

for player in players:
    player_id = player.get("id")
    team_id = player.get("team")
    position_id = player.get("element_type")

    team_data = team_lookup.get(team_id, {})

    name = player.get("web_name", "Unknown")
    position = positions.get(position_id, "?")
    team_name = team_data.get("short_name", "?")

    price = number(player.get("now_cost")) / 10
    points = number(player.get("total_points"))
    form = number(player.get("form"))
    minutes = number(player.get("minutes"))
    points_per_game = number(player.get("points_per_game"))
    selected = number(player.get("selected_by_percent"))

    goals = number(player.get("goals_scored"))
    assists = number(player.get("assists"))

    expected_goals = number(player.get("expected_goals"))
    expected_assists = number(player.get("expected_assists"))

    expected_goal_involvements = (
        expected_goals + expected_assists
    )

    bonus = number(player.get("bonus"))
    ict_index = number(player.get("ict_index"))
    influence = number(player.get("influence"))
    creativity = number(player.get("creativity"))
    threat = number(player.get("threat"))

    chance_this_round = number(
        player.get("chance_of_playing_this_round"),
        100
    )

    chance_next_round = number(
        player.get("chance_of_playing_next_round"),
        100
    )

    if player.get("chance_of_playing_this_round") is None:
        chance_this_round = 100

    if player.get("chance_of_playing_next_round") is None:
        chance_next_round = 100

    status = player.get("status")

    # --------------------------------------------------------
    # UPCOMING FIXTURES
    # --------------------------------------------------------

    upcoming = []

    for fixture in fixture_map.get(team_id, []):
        if (
            current_event is not None
            and fixture["event"] <= current_event
        ):
            continue

        upcoming.append(fixture)

    upcoming.sort(
        key=lambda x: x["event"]
    )

    upcoming = upcoming[:UPCOMING_FIXTURES]

    # --------------------------------------------------------
    # FIXTURE SCORE
    # --------------------------------------------------------

    difficulty_values = [
        number(
            fixture.get("difficulty"),
            3
        )
        for fixture in upcoming
    ]

    if difficulty_values:
        average_difficulty = (
            sum(difficulty_values)
            / len(difficulty_values)
        )
    else:
        average_difficulty = 3

    fixture_score = clamp(
        6 - average_difficulty,
        0,
        5
    )

    # --------------------------------------------------------
    # COMPONENT SCORES
    # --------------------------------------------------------

    minutes_score = clamp(
        minutes / 1000,
        0,
        1
    )

    form_score = clamp(
        form / 10,
        0,
        2
    )

    points_score = clamp(
        points / 200,
        0,
        2
    )

    attack_score = clamp(
        expected_goal_involvements / 10,
        0,
        2
    )

    ict_score = clamp(
        ict_index / 200,
        0,
        1
    )

    availability_score = (
        chance_this_round / 100
    )

    # --------------------------------------------------------
    # FINAL AGENT SCORE
    # --------------------------------------------------------

    score = (
        form_score * 2.0
        + points_score * 1.5
        + points_per_game * 0.25
        + minutes_score * 1.0
        + fixture_score * 0.8
        + attack_score * 1.2
        + ict_score * 0.5
        + bonus * 0.02
        + availability_score * 1.0
    )

    if chance_this_round < 50:
        score *= 0.40
    elif chance_this_round < 75:
        score *= 0.70

    if price > 0:
        value_score = score / price
    else:
        value_score = 0

    analysed_players.append({
        "id": player_id,
        "name": name,
        "position": position,
        "position_id": position_id,
        "team_id": team_id,
        "team": team_name,
        "price": round(price, 1),
        "points": int(points),
        "form": round(form, 2),
        "minutes": int(minutes),
        "points_per_game": round(points_per_game, 2),
        "goals": int(goals),
        "assists": int(assists),
        "expected_goals": round(expected_goals, 2),
        "expected_assists": round(expected_assists, 2),
        "expected_goal_involvements": round(
            expected_goal_involvements,
            2
        ),
        "bonus": int(bonus),
        "ict_index": round(ict_index, 2),
        "influence": round(influence, 2),
        "creativity": round(creativity, 2),
        "threat": round(threat, 2),
        "selected_by_percent": round(selected, 2),
        "chance_this_round": chance_this_round,
        "chance_next_round": chance_next_round,
        "status": status,
        "average_fixture_difficulty": round(
            average_difficulty,
            2
        ),
        "fixture_score": round(
            fixture_score,
            2
        ),
        "agent_score": round(
            score,
            3
        ),
        "value_score": round(
            value_score,
            3
        ),
        "upcoming_fixtures": upcoming
    })


# ============================================================
# 10. SORT
# ============================================================

analysed_players.sort(
    key=lambda x: x["agent_score"],
    reverse=True
)


# ============================================================
# 11. TOP PLAYERS
# ============================================================

print("")
print("====================================")
print("       TOP PLAYER ANALYSIS")
print("====================================")

for index, player in enumerate(
    analysed_players[:TOP_PLAYERS],
    1
):
    print(
        f"{index}. "
        f"{player['name']} | "
        f"{player['team']} | "
        f"{player['position']} | "
        f"Score {player['agent_score']} | "
        f"Form {player['form']} | "
        f"Points {player['points']} | "
        f"Min {player['minutes']} | "
        f"Price {player['price']}"
    )


# ============================================================
# 12. BEST PLAYERS BY POSITION
# ============================================================

def best_by_position(position, count):
    candidates = [
        player
        for player in analysed_players
        if player["position"] == position
    ]

    return candidates[:count]


best_goalkeepers = best_by_position("GK", 5)
best_defenders = best_by_position("DEF", 10)
best_midfielders = best_by_position("MID", 10)
best_forwards = best_by_position("FWD", 10)


# ============================================================
# 13. MODEL STARTING XI
# ============================================================

formations = [
    (3, 4, 3),
    (3, 5, 2),
    (4, 3, 3),
    (4, 4, 2),
    (4, 5, 1),
    (5, 3, 2),
    (5, 4, 1)
]


def team_count_ok(selected, candidate):
    same_team = sum(
        1
        for player in selected
        if player["team_id"] == candidate["team_id"]
    )

    return same_team < 3


def build_lineup(formation):
    defenders_needed = formation[0]
    midfielders_needed = formation[1]
    forwards_needed = formation[2]

    lineup = []

    # GK
    for player in best_by_position("GK", 20):
        if team_count_ok(lineup, player):
            lineup.append(player)
            break

    # DEF
    for player in best_by_position("DEF", 30):
        if len([
            x for x in lineup
            if x["position"] == "DEF"
        ]) >= defenders_needed:
            break

        if team_count_ok(lineup, player):
            lineup.append(player)

    # MID
    for player in best_by_position("MID", 40):
        if len([
            x for x in lineup
            if x["position"] == "MID"
        ]) >= midfielders_needed:
            break

        if team_count_ok(lineup, player):
            lineup.append(player)

    # FWD
    for player in best_by_position("FWD", 30):
        if len([
            x for x in lineup
            if x["position"] == "FWD"
        ]) >= forwards_needed:
            break

        if team_count_ok(lineup, player):
            lineup.append(player)

    if len(lineup) != 11:
        return None

    total_cost = sum(
        player["price"]
        for player in lineup
    )

    total_score = sum(
        player["agent_score"]
        for player in lineup
    )

    return {
        "formation": formation,
        "players": lineup,
        "cost": round(total_cost, 1),
        "score": round(total_score, 3)
    }


model_lineups = []

for formation in formations:
    lineup = build_lineup(formation)

    if lineup:
        model_lineups.append(lineup)


model_lineups.sort(
    key=lambda x: x["score"],
    reverse=True
)

best_model_lineup = (
    model_lineups[0]
    if model_lineups
    else None
)


# ============================================================
# 14. CAPTAIN / VICE CAPTAIN
# ============================================================

captain_candidates = []

if best_model_lineup:
    captain_candidates = sorted(
        best_model_lineup["players"],
        key=lambda x: (
            x["agent_score"]
            + x["fixture_score"]
            + x["expected_goal_involvements"] * 0.5
        ),
        reverse=True
    )

captain = (
    captain_candidates[0]
    if len(captain_candidates) > 0
    else None
)

vice_captain = (
    captain_candidates[1]
    if len(captain_candidates) > 1
    else None
)


# ============================================================
# 15. PRINT LINEUP
# ============================================================

print("")
print("====================================")
print("       MODEL STARTING XI")
print("====================================")

if best_model_lineup:
    print(
        "Formation:",
        best_model_lineup["formation"]
    )

    print(
        "Cost:",
        best_model_lineup["cost"]
    )

    print(
        "Score:",
        best_model_lineup["score"]
    )

    print("")

    for player in best_model_lineup["players"]:
        print(
            player["position"],
            "|",
            player["name"],
            "|",
            player["team"],
            "| Score:",
            player["agent_score"]
        )
else:
    print("Could not build model XI.")


# ============================================================
# 16. CAPTAIN
# ============================================================

print("")
print("====================================")
print("       CAPTAIN ANALYSIS")
print("====================================")

if captain:
    print(
        "Captain:",
        captain["name"],
        "|",
        captain["team"],
        "| Score:",
        captain["agent_score"]
    )
else:
    print("Captain unavailable.")

if vice_captain:
    print(
        "Vice-Captain:",
        vice_captain["name"],
        "|",
        vice_captain["team"],
        "| Score:",
        vice_captain["agent_score"]
    )


# ============================================================
# 17. TRANSFER CANDIDATES
# ============================================================

print("")
print("====================================")
print("       TRANSFER CANDIDATES")
print("====================================")

transfer_candidates = []

current_player_ids = set()

if current_picks:
    current_player_ids = {
        pick["element"]
        for pick in current_picks.get("picks", [])
        if pick.get("element") is not None
    }

    transfer_candidates = [
        player
        for player in analysed_players
        if player["id"] not in current_player_ids
    ]

    print(
        "Transfer analysis based on squad GW:",
        squad_gameweek
    )
else:
    # No squad data means we must NOT pretend these are
    # actual transfer recommendations for the user's team.
    transfer_candidates = analysed_players

    print(
        "WARNING: squad unavailable; "
        "showing general player targets only."
    )


for index, player in enumerate(
    transfer_candidates[:20],
    1
):
    print(
        f"{index}. "
        f"{player['name']} | "
        f"{player['position']} | "
        f"{player['team']} | "
        f"Score {player['agent_score']} | "
        f"Value {player['value_score']}"
    )


# ============================================================
# 18. CHIP DATA
# ============================================================

chips = {
    "wildcard": None,
    "free_hit": None,
    "bench_boost": None,
    "triple_captain": None
}

try:
    history = get_json(
        f"{BASE_URL}/entry/"
        f"{TEAM_ID}/history/"
    )

    chips_used = history.get(
        "chips",
        []
    )

    chips["history"] = chips_used

except Exception as error:
    print(
        "Chip history not available:",
        error
    )

    chips["history"] = []


# ============================================================
# 19. BUDGET
# ============================================================

team_value_raw = number(
    team.get("last_deadline_value")
)

if team_value_raw > 0:
    team_value = team_value_raw / 10
else:
    team_value = None

bank = number(
    team.get("last_deadline_bank")
)

if bank > 0:
    bank = bank / 10
else:
    bank = None

budget_data = {
    "team_value": team_value,
    "bank": bank,
    "last_deadline_value_raw":
        team.get("last_deadline_value"),
    "last_deadline_bank_raw":
        team.get("last_deadline_bank")
}


# ============================================================
# 20. FINAL DATA OBJECT
# ============================================================

output = {
    "agent": {
        "name": "FPL Autonomous Agent",
        "version": "1.1",
        "generated_at":
            datetime.now(timezone.utc).isoformat()
    },

    "team": team,

    "team_id": TEAM_ID,

    "current_gameweek": current_event,

    "budget": budget_data,

    "players": players,

    "analysed_players": analysed_players,

    "gameweeks": events,

    "fpl_teams": teams,

    "fixtures": fixtures,

    "current_picks": current_picks,

    "squad_gameweek": squad_gameweek,

    "squad_source": squad_source,

    "model_lineups": model_lineups,

    "best_model_lineup": best_model_lineup,

    "captain": captain,

    "vice_captain": vice_captain,

    "transfer_candidates": transfer_candidates[:50],

    "chips": chips
}


# ============================================================
# 21. SAVE JSON
# ============================================================

with open(
    "fpl_data.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        output,
        file,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 22. FINAL STATUS
# ============================================================

print("")
print("====================================")
print("       DATA SAVED")
print("====================================")

print(
    "FPL data saved to fpl_data.json"
)

print(
    "Analysed players:",
    len(analysed_players)
)

print(
    "Transfer candidates:",
    len(transfer_candidates)
)

if current_picks:
    print(
        "Real squad data: AVAILABLE"
    )
else:
    print(
        "Real squad data: NOT AVAILABLE"
    )

print("")
print(
    "Agent connected successfully."
)

