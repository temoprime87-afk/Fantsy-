import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

TEAM_ID = 9623737

BASE_URL = "https://fantasy.premierleague.com/api"

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) "
    "AppleWebKit/537.36 Chrome/140 Safari/537.36"
)

TOP_PLAYERS = 30
TOP_TRANSFERS = 20
UPCOMING_FIXTURES = 5


# ============================================================
# API
# ============================================================

def get_json(url, retries=3):

    last_error = None

    for attempt in range(retries):

        try:

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Referer": "https://fantasy.premierleague.com/"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                data = response.read().decode("utf-8")

                return json.loads(data)

        except urllib.error.HTTPError as error:

            last_error = (
                f"HTTP {error.code}: {error.reason}"
            )

            if error.code in [404, 403]:
                break

        except urllib.error.URLError as error:

            last_error = (
                f"Network error: {error.reason}"
            )

        except Exception as error:

            last_error = str(error)

    raise RuntimeError(
        f"{last_error} - {url}"
    )


# ============================================================
# SAFE HELPERS
# ============================================================

def number(value, default=0.0):

    try:

        if value is None:
            return default

        return float(value)

    except Exception:

        return default


def integer(value, default=0):

    try:

        if value is None:
            return default

        return int(value)

    except Exception:

        return default


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(maximum, value)
    )


# ============================================================
# START
# ============================================================

print("")
print("========================================")
print("        FPL AUTONOMOUS AGENT")
print("========================================")
print("")


# ============================================================
# 1. TEAM
# ============================================================

print("Loading team data...")

team = get_json(
    f"{BASE_URL}/entry/{TEAM_ID}/"
)

print(
    "Team:",
    team.get("name", "Unknown")
)

print(
    "Manager:",
    team.get("player_first_name", ""),
    team.get("player_last_name", "")
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

players = bootstrap.get(
    "elements",
    []
)

events = bootstrap.get(
    "events",
    []
)

teams = bootstrap.get(
    "teams",
    []
)

print(
    "Players loaded:",
    len(players)
)

print(
    "Gameweeks loaded:",
    len(events)
)

print(
    "FPL teams loaded:",
    len(teams)
)


# ============================================================
# 3. CURRENT GAMEWEEK
# ============================================================

current_event = None

for event in events:

    if event.get("is_current"):

        current_event = event.get("id")
        break


if current_event is None:

    for event in events:

        if event.get("is_next"):

            current_event = event.get("id")
            break


if current_event is None:

    current_event = integer(
        team.get("current_event"),
        1
    )


print("")
print(
    "Current Gameweek:",
    current_event
)


# ============================================================
# 4. FIXTURES
# ============================================================

print("")
print("Loading fixtures...")

fixtures = get_json(
    f"{BASE_URL}/fixtures/"
)

print(
    "Fixtures loaded:",
    len(fixtures)
)


# ============================================================
# 5. TEAM LOOKUP
# ============================================================

team_lookup = {}

for fpl_team in teams:

    team_lookup[
        fpl_team.get("id")
    ] = fpl_team


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


    home_difficulty = fixture.get(
        "team_h_difficulty",
        3
    )

    away_difficulty = fixture.get(
        "team_a_difficulty",
        3
    )


    fixture_map.setdefault(
        home_team,
        []
    ).append({

        "event": event,

        "opponent": away_team,

        "home": True,

        "difficulty":
            home_difficulty,

        "finished":
            fixture.get(
                "finished",
                False
            ),

        "kickoff":
            fixture.get(
                "kickoff_time"
            )

    })


    fixture_map.setdefault(
        away_team,
        []
    ).append({

        "event": event,

        "opponent": home_team,

        "home": False,

        "difficulty":
            away_difficulty,

        "finished":
            fixture.get(
                "finished",
                False
            ),

        "kickoff":
            fixture.get(
                "kickoff_time"
            )

    })


# ============================================================
# 8. REAL CURRENT SQUAD
# ============================================================

print("")
print("Loading real squad...")


current_picks = None

current_player_ids = set()

squad_event_used = None


# First try current GW.
# If unavailable, try previous GWs.
# This fixes the common 404 problem.

events_to_try = []


if current_event:

    events_to_try.append(
        current_event
    )


for event_id in range(
    integer(current_event, 1) - 1,
    0,
    -1
):

    if event_id not in events_to_try:

        events_to_try.append(
            event_id
        )


for event_id in events_to_try:

    try:

        print(
            "Trying squad GW:",
            event_id
        )

        squad_data = get_json(

            f"{BASE_URL}/entry/"
            f"{TEAM_ID}/event/"
            f"{event_id}/picks/"

        )

        picks = squad_data.get(
            "picks",
            []
        )


        if picks:

            current_picks = squad_data

            squad_event_used = event_id

            current_player_ids = {

                pick.get("element")

                for pick in picks

                if pick.get("element")
                is not None

            }

            print(
                "REAL SQUAD LOADED:",
                len(current_player_ids),
                "players"
            )

            print(
                "Squad Gameweek:",
                squad_event_used
            )

            break


    except Exception as error:

        print(
            "GW",
            event_id,
            "not available."
        )


if not current_player_ids:

    print("")
    print(
        "WARNING: REAL SQUAD NOT AVAILABLE."
    )

    print(
        "Agent will continue with general targets."
    )

else:

    print(
        "Real squad connected successfully."
    )


# ============================================================
# 9. PLAYER ANALYSIS
# ============================================================

print("")
print("Analysing players...")


analysed_players = []


for player in players:

    player_id = player.get(
        "id"
    )

    team_id = player.get(
        "team"
    )

    position_id = player.get(
        "element_type"
    )


    team_data = team_lookup.get(
        team_id,
        {}
    )


    name = player.get(
        "web_name",
        "Unknown"
    )


    position = positions.get(
        position_id,
        "?"
    )


    team_name = team_data.get(
        "short_name",
        "?"
    )


    price = (
        number(
            player.get(
                "now_cost"
            )
        )
        / 10
    )


    points = number(
        player.get(
            "total_points"
        )
    )


    form = number(
        player.get(
            "form"
        )
    )


    minutes = number(
        player.get(
            "minutes"
        )
    )


    points_per_game = number(
        player.get(
            "points_per_game"
        )
    )


    selected = number(
        player.get(
            "selected_by_percent"
        )
    )


    goals = number(
        player.get(
            "goals_scored"
        )
    )


    assists = number(
        player.get(
            "assists"
        )
    )


    expected_goals = number(
        player.get(
            "expected_goals"
        )
    )


    expected_assists = number(
        player.get(
            "expected_assists"
        )
    )


    expected_goal_involvements = (
        expected_goals
        + expected_assists
    )


    bonus = number(
        player.get(
            "bonus"
        )
    )


    ict_index = number(
        player.get(
            "ict_index"
        )
    )


    influence = number(
        player.get(
            "influence"
        )
    )


    creativity = number(
        player.get(
            "creativity"
        )
    )


    threat = number(
        player.get(
            "threat"
        )
    )


    chance_this_round = number(
        player.get(
            "chance_of_playing_this_round"
        ),
        100
    )


    chance_next_round = number(
        player.get(
            "chance_of_playing_next_round"
        ),
        100
    )


    if player.get(
        "chance_of_playing_this_round"
    ) is None:

        chance_this_round = 100


    if player.get(
        "chance_of_playing_next_round"
    ) is None:

        chance_next_round = 100


    status = player.get(
        "status"
    )


    # ========================================================
    # UPCOMING FIXTURES
    # ========================================================

    upcoming = []


    for fixture in fixture_map.get(
        team_id,
        []
    ):

        if (
            current_event is not None
            and fixture["event"]
            <= current_event
        ):

            continue


        upcoming.append(
            fixture
        )


    upcoming.sort(
        key=lambda x: x["event"]
    )


    upcoming = upcoming[
        :UPCOMING_FIXTURES
    ]


    difficulty_values = [

        number(
            fixture.get(
                "difficulty"
            ),
            3
        )

        for fixture in upcoming

    ]


    if difficulty_values:

        average_difficulty = (
            sum(difficulty_values)
            /
            len(difficulty_values)
        )

    else:

        average_difficulty = 3


    fixture_score = clamp(

        6 - average_difficulty,

        0,

        5

    )


    # ========================================================
    # SCORE COMPONENTS
    # ========================================================

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


    # ========================================================
    # FINAL SCORE
    # ========================================================

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

        value_score = (
            score / price
        )

    else:

        value_score = 0


    analysed_players.append({

        "id":
            player_id,

        "name":
            name,

        "position":
            position,

        "position_id":
            position_id,

        "team_id":
            team_id,

        "team":
            team_name,

        "price":
            round(price, 1),

        "points":
            int(points),

        "form":
            round(form, 2),

        "minutes":
            int(minutes),

        "points_per_game":
            round(points_per_game, 2),

        "goals":
            int(goals),

        "assists":
            int(assists),

        "expected_goals":
            round(expected_goals, 2),

        "expected_assists":
            round(expected_assists, 2),

        "expected_goal_involvements":
            round(
                expected_goal_involvements,
                2
            ),

        "bonus":
            int(bonus),

        "ict_index":
            round(ict_index, 2),

        "influence":
            round(influence, 2),

        "creativity":
            round(creativity, 2),

        "threat":
            round(threat, 2),

        "selected_by_percent":
            round(selected, 2),

        "chance_this_round":
            chance_this_round,

        "chance_next_round":
            chance_next_round,

        "status":
            status,

        "average_fixture_difficulty":
            round(
                average_difficulty,
                2
            ),

        "fixture_score":
            round(
                fixture_score,
                2
            ),

        "agent_score":
            round(
                score,
                3
            ),

        "value_score":
            round(
                value_score,
                3
            ),

        "upcoming_fixtures":
            upcoming

    })


# ============================================================
# 10. SORT PLAYERS
# ============================================================

analysed_players.sort(

    key=lambda x:
    x["agent_score"],

    reverse=True

)


# ============================================================
# 11. TOP PLAYERS
# ============================================================

print("")
print("========================================")
print("          TOP PLAYER ANALYSIS")
print("========================================")


for index, player in enumerate(

    analysed_players[
        :TOP_PLAYERS
    ],

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
# 12. POSITION HELPERS
# ============================================================

def players_by_position(
    position
):

    return [

        player

        for player in analysed_players

        if player["position"] == position

    ]


# ============================================================
# 13. BEST XI
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


def team_count_ok(
    selected,
    candidate
):

    count = sum(

        1

        for player in selected

        if player["team_id"]
        == candidate["team_id"]

    )

    return count < 3


def build_lineup(
    formation
):

    defenders_needed = formation[0]

    midfielders_needed = formation[1]

    forwards_needed = formation[2]


    lineup = []


    # GK

    for player in players_by_position(
        "GK"
    ):

        if team_count_ok(
            lineup,
            player
        ):

            lineup.append(
                player
            )

            break


    # DEF

    for player in players_by_position(
        "DEF"
    ):

        current_count = sum(

            1

            for x in lineup

            if x["position"] == "DEF"

        )


        if current_count >= defenders_needed:

            break


        if team_count_ok(
            lineup,
            player
        ):

            lineup.append(
                player
            )


    # MID

    for player in players_by_position(
        "MID"
    ):

        current_count = sum(

            1

            for x in lineup

            if x["position"] == "MID"

        )


        if current_count >= midfielders_needed:

            break


        if team_count_ok(
            lineup,
            player
        ):

            lineup.append(
                player
            )


    # FWD

    for player in players_by_position(
        "FWD"
    ):

        current_count = sum(

            1

            for x in lineup

            if x["position"] == "FWD"

        )


        if current_count >= forwards_needed:

            break


        if team_count_ok(
            lineup,
            player
        ):

            lineup.append(
                player
            )


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

        "formation":
            formation,

        "players":
            lineup,

        "cost":
            round(
                total_cost,
                1
            ),

        "score":
            round(
                total_score,
                3
            )

    }


model_lineups = []


for formation in formations:

    lineup = build_lineup(
        formation
    )

    if lineup:

        model_lineups.append(
            lineup
        )


model_lineups.sort(

    key=lambda x:
    x["score"],

    reverse=True

)


best_model_lineup = (

    model_lineups[0]

    if model_lineups

    else None

)


# ============================================================
# 14. CAPTAIN / VICE
# ============================================================

captain_candidates = []


if best_model_lineup:

    captain_candidates = sorted(

        best_model_lineup[
            "players"
        ],

        key=lambda x: (

            x["agent_score"]

            + x["fixture_score"]

            + (
                x["expected_goal_involvements"]
                * 0.5
            )

        ),

        reverse=True

    )


captain = (

    captain_candidates[0]

    if captain_candidates

    else None

)


vice_captain = (

    captain_candidates[1]

    if len(captain_candidates) > 1

    else None

)


# ============================================================
# 15. MODEL XI OUTPUT
# ============================================================

print("")
print("========================================")
print("          MODEL STARTING XI")
print("========================================")


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


    for player in best_model_lineup[
        "players"
    ]:

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

    print(
        "Could not build model XI."
    )


# ============================================================
# 16. CAPTAIN OUTPUT
# ============================================================

print("")
print("========================================")
print("          CAPTAIN ANALYSIS")
print("========================================")


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

    print(
        "Captain unavailable."
    )


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
# 17. TRANSFER ANALYSIS
# ============================================================

print("")
print("========================================")
print("          TRANSFER ANALYSIS")
print("========================================")


if current_player_ids:

    print(
        "Using REAL squad."
    )

    print(
        "Current squad size:",
        len(current_player_ids)
    )


    current_squad = [

        player

        for player in analysed_players

        if player["id"]
        in current_player_ids

    ]


    transfer_candidates = [

        player

        for player in analysed_players

        if player["id"]
        not in current_player_ids

    ]


else:

    print(
        "Real squad unavailable."
    )

    print(
        "Using general targets."
    )


    current_squad = []

    transfer_candidates = (
        analysed_players
    )


# ============================================================
# 18. CURRENT SQUAD ANALYSIS
# ============================================================

if current_squad:

    print("")
    print("CURRENT SQUAD PLAYERS")
    print("----------------------------------------")


    current_squad.sort(

        key=lambda x:
        x["agent_score"],

        reverse=True

    )


    for player in current_squad:

        print(

            player["position"],
            "|",
            player["name"],
            "|",
            player["team"],
            "| Score:",
            player["agent_score"],
            "| Price:",
            player["price"]

        )


# ============================================================
# 19. TRANSFER TARGETS
# ============================================================

print("")
print("TRANSFER TARGETS")
print("----------------------------------------")


for index, player in enumerate(

    transfer_candidates[
        :TOP_TRANSFERS
    ],

    1

):

    print(

        f"{index}. "
        f"{player['name']} | "
        f"{player['position']} | "
        f"{player['team']} | "
        f"Score {player['agent_score']} | "
        f"Value {player['value_score']} | "
        f"Price {player['price']}"

    )


# ============================================================
# 20. POSSIBLE SELL CANDIDATES
# ============================================================

sell_candidates = []


if current_squad:

    sell_candidates = sorted(

        current_squad,

        key=lambda x:
        x["agent_score"]

    )


    print("")
    print("POSSIBLE SELL CANDIDATES")
    print("----------------------------------------")


    for index, player in enumerate(

        sell_candidates[:10],

        1

    ):

        print(

            f"{index}. "
            f"{player['name']} | "
            f"{player['position']} | "
            f"{player['team']} | "
            f"Score {player['agent_score']} | "
            f"Price {player['price']}"

        )


# ============================================================
# 21. BUDGET
# ============================================================

team_value_raw = number(
    team.get(
        "last_deadline_value"
    )
)


bank_raw = number(
    team.get(
        "last_deadline_bank"
    )
)


team_value = (

    team_value_raw / 10

    if team_value_raw > 0

    else None

)


bank = (

    bank_raw / 10

    if bank_raw > 0

    else None

)


budget_data = {

    "team_value":
        team_value,

    "bank":
        bank,

    "raw_team_value":
        team_value_raw,

    "raw_bank":
        bank_raw

}


print("")
print("========================================")
print("             BUDGET")
print("========================================")


print(
    "Team value:",
    team_value
)


print(
    "Bank:",
    bank
)


# ============================================================
# 22. CHIP HISTORY
# ============================================================

print("")
print("Loading chip history...")


chips_history = []


try:

    history = get_json(

        f"{BASE_URL}/entry/"
        f"{TEAM_ID}/history/"

    )


    chips_history = history.get(
        "chips",
        []
    )


    print(
        "Chips found:",
        len(chips_history)
    )


except Exception as error:

    print(
        "Chip history unavailable:",
        error
    )


# ============================================================
# 23. FINAL OUTPUT
# ============================================================

output = {

    "agent": {

        "name":
            "FPL Autonomous Agent",

        "version":
            "2.0",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat()

    },

    "team_id":
        TEAM_ID,

    "team":
        team,

    "current_gameweek":
        current_event,

    "squad_gameweek_used":
        squad_event_used,

    "real_squad_available":
        bool(current_player_ids),

    "budget":
        budget_data,

    "players":
        players,

    "analysed_players":
        analysed_players,

    "events":
        events,

    "fpl_teams":
        teams,

    "fixtures":
        fixtures,

    "current_picks":
        current_picks,

    "current_squad":
        current_squad,

    "model_lineups":
        model_lineups,

    "best_model_lineup":
        best_model_lineup,

    "captain":
        captain,

    "vice_captain":
        vice_captain,

    "transfer_candidates":
        transfer_candidates[:50],

    "sell_candidates":
        sell_candidates[:20],

    "chips":
        chips_history

}


# ============================================================
# 24. SAVE JSON
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
# 25. FINAL STATUS
# ============================================================

print("")
print("========================================")
print("              DATA SAVED")
print("========================================")


print(
    "File: fpl_data.json"
)


print(
    "Analysed players:",
    len(analysed_players)
)


print(
    "Real squad available:",
    bool(current_player_ids)
)


print(
    "Squad GW used:",
    squad_event_used
)


print(
    "Transfer candidates:",
    len(transfer_candidates)
)


if captain:

    print(
        "Captain:",
        captain["name"]
    )


if vice_captain:

    print(
        "Vice-Captain:",
        vice_captain["name"]
    )


print("")
print(
    "AGENT CONNECTED SUCCESSFULLY."
)
print("========================================")
