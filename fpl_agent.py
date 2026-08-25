import json
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

TEAM_ID = 9623737

BASE_URL = "https://fantasy.premierleague.com/api"

BUDGET = 100.0

TOP_PLAYERS = 30
UPCOMING_FIXTURES = 5

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36"
)


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
                    "Referer": "https://fantasy.premierleague.com/",
                    "Origin": "https://fantasy.premierleague.com",
                    "X-Requested-With": "XMLHttpRequest"
                },
                method="GET"
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                raw = response.read().decode("utf-8")

                return json.loads(raw)

        except urllib.error.HTTPError as error:

            last_error = (
                f"HTTP {error.code}: {error.reason}"
            )

            if error.code in [403, 429, 500, 502, 503, 504]:

                time.sleep(2 + attempt * 2)
                continue

            break

        except urllib.error.URLError as error:

            last_error = f"Network error: {error.reason}"

            time.sleep(2 + attempt * 2)

        except Exception as error:

            last_error = str(error)

            time.sleep(2 + attempt * 2)

    raise RuntimeError(
        f"{last_error} | URL: {url}"
    )


# ============================================================
# HELPERS
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


def money(value):

    return round(
        number(value) / 10,
        1
    )


# ============================================================
# START
# ============================================================

print("")
print("========================================")
print("       FPL AUTONOMOUS AGENT v5")
print("========================================")
print("")

print("Team ID:", TEAM_ID)
print("New squad budget: £", BUDGET)


# ============================================================
# 1. TEAM DATA
# ============================================================

print("")
print("Loading team data...")

try:

    team = get_json(
        f"{BASE_URL}/entry/{TEAM_ID}/"
    )

    print(
        "Team:",
        team.get("name", "Unknown")
    )

except Exception as error:

    print(
        "WARNING: Team data unavailable:",
        error
    )

    team = {
        "name": "Unknown",
        "current_event": 1
    }


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
# 3. TARGET GAMEWEEK
# ============================================================

target_event = None

for event in events:

    if event.get("is_next"):

        target_event = integer(
            event.get("id")
        )

        break


if target_event is None:

    for event in events:

        if event.get("is_current"):

            target_event = integer(
                event.get("id")
            )

            break


if target_event is None:

    target_event = integer(
        team.get(
            "current_event"
        ),
        1
    )


if target_event <= 0:

    target_event = 1


current_event = target_event


print("")
print(
    "TARGET GAMEWEEK:",
    current_event
)


# ============================================================
# 4. FIXTURES
# ============================================================

print("")
print("Loading fixtures...")

try:

    fixtures = get_json(
        f"{BASE_URL}/fixtures/"
    )

except Exception as error:

    print(
        "WARNING: Fixtures unavailable:",
        error
    )

    fixtures = []


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
# 6. POSITIONS
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

    event = fixture.get(
        "event"
    )

    if event is None:
        continue

    home_team = fixture.get(
        "team_h"
    )

    away_team = fixture.get(
        "team_a"
    )

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

        "difficulty": home_difficulty,

        "finished": fixture.get(
            "finished",
            False
        ),

        "kickoff": fixture.get(
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

        "difficulty": away_difficulty,

        "finished": fixture.get(
            "finished",
            False
        ),

        "kickoff": fixture.get(
            "kickoff_time"
        )

    })


# ============================================================
# 8. PLAYER ANALYSIS
# ============================================================

print("")
print("Analysing players...")

analysed_players = []


for player in players:

    player_id = integer(
        player.get("id")
    )

    team_id = integer(
        player.get("team")
    )

    position_id = integer(
        player.get("element_type")
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

    price = money(
        player.get("now_cost")
    )

    points = number(
        player.get("total_points")
    )

    form = number(
        player.get("form")
    )

    minutes = number(
        player.get("minutes")
    )

    points_per_game = number(
        player.get("points_per_game")
    )

    goals = number(
        player.get("goals_scored")
    )

    assists = number(
        player.get("assists")
    )

    expected_goals = number(
        player.get("expected_goals")
    )

    expected_assists = number(
        player.get("expected_assists")
    )

    xgi = (
        expected_goals
        +
        expected_assists
    )

    bonus = number(
        player.get("bonus")
    )

    ict_index = number(
        player.get("ict_index")
    )

    influence = number(
        player.get("influence")
    )

    creativity = number(
        player.get("creativity")
    )

    threat = number(
        player.get("threat")
    )

    selected = number(
        player.get("selected_by_percent")
    )

    chance_current = player.get(
        "chance_of_playing_this_round"
    )

    chance_next = player.get(
        "chance_of_playing_next_round"
    )

    if chance_current is None:

        chance_current = 100

    else:

        chance_current = number(
            chance_current
        )

    if chance_next is None:

        chance_next = 100

    else:

        chance_next = number(
            chance_next
        )

    status = player.get(
        "status"
    )


    # --------------------------------------------------------
    # TARGET GAMEWEEK FIXTURE
    # --------------------------------------------------------

    upcoming = []

    for fixture in fixture_map.get(
        team_id,
        []
    ):

        fixture_event = integer(
            fixture.get("event")
        )

        if fixture_event != current_event:
            continue

        if fixture.get("finished"):
            continue

        upcoming.append(
            fixture
        )


    # --------------------------------------------------------
    # UPCOMING FIXTURES AFTER TARGET
    # --------------------------------------------------------

    future_fixtures = []

    for fixture in fixture_map.get(
        team_id,
        []
    ):

        fixture_event = integer(
            fixture.get("event")
        )

        if fixture_event <= current_event:
            continue

        if fixture.get("finished"):
            continue

        future_fixtures.append(
            fixture
        )

    future_fixtures.sort(
        key=lambda x:
        integer(
            x.get("event")
        )
    )

    future_fixtures = future_fixtures[
        :UPCOMING_FIXTURES
    ]


    # --------------------------------------------------------
    # FIXTURE DIFFICULTY
    # --------------------------------------------------------

    fixture_difficulties = [

        number(
            f.get(
                "difficulty"
            ),
            3
        )

        for f in upcoming

    ]

    if fixture_difficulties:

        average_difficulty = (
            sum(fixture_difficulties)
            /
            len(fixture_difficulties)
        )

    else:

        average_difficulty = 5


    fixture_score = clamp(
        6 - average_difficulty,
        0,
        5
    )


    # --------------------------------------------------------
    # HAS GAME THIS WEEK?
    # --------------------------------------------------------

    has_fixture = len(
        upcoming
    ) > 0


    if has_fixture:

        playing_bonus = 2.0

    else:

        playing_bonus = -6.0


    # --------------------------------------------------------
    # COMPONENT SCORES
    # --------------------------------------------------------

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

    minutes_score = clamp(
        minutes / 1000,
        0,
        1
    )

    attack_score = clamp(
        xgi / 10,
        0,
        2
    )

    ict_score = clamp(
        ict_index / 200,
        0,
        1
    )

    availability_score = (
        chance_current / 100
    )


    # --------------------------------------------------------
    # POSITION WEIGHTS
    # --------------------------------------------------------

    if position == "FWD":

        attack_weight = 1.50
        fixture_weight = 1.00

    elif position == "MID":

        attack_weight = 1.40
        fixture_weight = 1.00

    elif position == "DEF":

        attack_weight = 0.75
        fixture_weight = 1.15

    else:

        attack_weight = 0.40
        fixture_weight = 1.20


    # --------------------------------------------------------
    # AGENT SCORE
    # --------------------------------------------------------

    score = (

        form_score * 2.0

        +
        points_score * 1.4

        +
        points_per_game * 0.25

        +
        minutes_score * 1.0

        +
        fixture_score * fixture_weight

        +
        attack_score * attack_weight

        +
        ict_score * 0.5

        +
        bonus * 0.02

        +
        availability_score * 1.0

        +
        playing_bonus

    )


    # --------------------------------------------------------
    # AVAILABILITY PENALTY
    # --------------------------------------------------------

    if chance_current < 50:

        score *= 0.35

    elif chance_current < 75:

        score *= 0.65

    elif chance_current < 90:

        score *= 0.90


    # --------------------------------------------------------
    # VALUE SCORE
    # --------------------------------------------------------

    if price > 0:

        value_score = (
            score / price
        )

    else:

        value_score = 0


    # --------------------------------------------------------
    # PLAYER RECORD
    # --------------------------------------------------------

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
            price,

        "points":
            int(points),

        "form":
            round(
                form,
                2
            ),

        "minutes":
            int(minutes),

        "points_per_game":
            round(
                points_per_game,
                2
            ),

        "goals":
            int(goals),

        "assists":
            int(assists),

        "expected_goals":
            round(
                expected_goals,
                2
            ),

        "expected_assists":
            round(
                expected_assists,
                2
            ),

        "expected_goal_involvements":
            round(
                xgi,
                2
            ),

        "bonus":
            int(bonus),

        "ict_index":
            round(
                ict_index,
                2
            ),

        "influence":
            round(
                influence,
                2
            ),

        "creativity":
            round(
                creativity,
                2
            ),

        "threat":
            round(
                threat,
                2
            ),

        "selected_by_percent":
            round(
                selected,
                2
            ),

        "chance_this_round":
            chance_current,

        "chance_next_round":
            chance_next,

        "status":
            status,

        "has_fixture":
            has_fixture,

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
            upcoming,

        "future_fixtures":
            future_fixtures

    })


# ============================================================
# 9. SORT PLAYERS
# ============================================================

analysed_players.sort(
    key=lambda x:
    x["agent_score"],
    reverse=True
)


# ============================================================
# 10. POSITION FILTER
# ============================================================

def players_by_position(
    position
):

    return [

        p

        for p in analysed_players

        if p["position"] == position

    ]


# ============================================================
# 11. VALID PLAYER FILTER
# ============================================================

def valid_players(position):

    result = []

    for player in players_by_position(
        position
    ):

        # Must have a fixture
        if not player["has_fixture"]:
            continue

        # Must have reasonable chance of playing
        if player["chance_this_round"] < 75:
            continue

        result.append(player)

    return result


# ============================================================
# 12. BUILD 15-MAN SQUAD
# ============================================================

print("")
print("========================================")
print("       BUILDING £100M SQUAD")
print("========================================")


# FPL squad structure
REQUIRED_GK = 2
REQUIRED_DEF = 5
REQUIRED_MID = 5
REQUIRED_FWD = 3


# ------------------------------------------------------------
# Sort by value
# ------------------------------------------------------------

for position in [
    "GK",
    "DEF",
    "MID",
    "FWD"
]:

    valid_players(position).sort(
        key=lambda p:
        p["agent_score"],
        reverse=True
    )


# ------------------------------------------------------------
# Budget-aware greedy selection
# ------------------------------------------------------------

def build_15_squad():

    squad = []

    used_budget = 0.0

    club_counts = {}


    # --------------------------------------------------------
    # Required positional counts
    # --------------------------------------------------------

    requirements = [

        ("GK", REQUIRED_GK),
        ("DEF", REQUIRED_DEF),
        ("MID", REQUIRED_MID),
        ("FWD", REQUIRED_FWD)

    ]


    # --------------------------------------------------------
    # Candidate selection
    # --------------------------------------------------------

    for position, required in requirements:

        candidates = valid_players(
            position
        )

        selected_for_position = []

        for player in candidates:

            if len(
                selected_for_position
            ) >= required:

                break


            # Maximum 3 players per club
            current_club_count = club_counts.get(
                player["team_id"],
                0
            )

            if current_club_count >= 3:
                continue


            # Avoid spending too much too early
            remaining_positions = (
                15
                -
                (
                    len(squad)
                    +
                    len(selected_for_position)
                    +
                    1
                )
            )

            remaining_budget = (
                BUDGET
                -
                used_budget
                -
                player["price"]
            )

            if remaining_budget < 0:
                continue


            squad.append(
                player
            )

            selected_for_position.append(
                player
            )

            used_budget += player[
                "price"
            ]

            club_counts[
                player["team_id"]
            ] = (
                current_club_count
                +
                1
            )


    # --------------------------------------------------------
    # Check positional completeness
    # --------------------------------------------------------

    counts = {

        "GK": 0,
        "DEF": 0,
        "MID": 0,
        "FWD": 0

    }

    for player in squad:

        counts[
            player["position"]
        ] += 1


    if counts != {

        "GK": REQUIRED_GK,
        "DEF": REQUIRED_DEF,
        "MID": REQUIRED_MID,
        "FWD": REQUIRED_FWD

    }:

        return None


    if used_budget > BUDGET:

        return None


    return {

        "players":
            squad,

        "cost":
            round(
                used_budget,
                1
            ),

        "money_left":
            round(
                BUDGET - used_budget,
                1
            ),

        "club_counts":
            club_counts

    }


# ============================================================
# 13. BETTER BUDGET OPTIMIZATION
# ============================================================

def optimize_squad():

    # Start with cheapest valid players
    # Then upgrade positions using available money.

    squad = build_15_squad()

    if squad is None:

        return None


    current_players = squad[
        "players"
    ]


    def squad_score(players_list):

        return sum(

            p["agent_score"]

            for p in players_list

        )


    current_score = squad_score(
        current_players
    )


    improved = True


    while improved:

        improved = False

        best_upgrade = None

        best_upgrade_gain = 0


        for old_player in current_players:

            position = old_player[
                "position"
            ]

            for new_player in valid_players(
                position
            ):

                if new_player["id"] in [

                    p["id"]

                    for p in current_players

                ]:

                    continue


                # Club rule
                club_count = sum(

                    1

                    for p in current_players

                    if p["team_id"]
                    ==
                    new_player["team_id"]

                    and p["id"]
                    !=
                    old_player["id"]

                )

                if club_count >= 3:
                    continue


                new_cost = (

                    squad["cost"]

                    -
                    old_player["price"]

                    +
                    new_player["price"]

                )


                if new_cost > BUDGET:
                    continue


                new_score = (

                    current_score

                    -
                    old_player["agent_score"]

                    +
                    new_player["agent_score"]

                )


                gain = (
                    new_score
                    -
                    current_score
                )


                if gain > best_upgrade_gain:

                    best_upgrade_gain = gain

                    best_upgrade = (

                        old_player,
                        new_player,
                        new_cost,
                        new_score

                    )


        if best_upgrade:

            old_player, new_player, new_cost, new_score = best_upgrade

            index = current_players.index(
                old_player
            )

            current_players[index] = (
                new_player
            )

            squad["cost"] = round(
                new_cost,
                1
            )

            squad["money_left"] = round(
                BUDGET - new_cost,
                1
            )

            current_score = new_score

            improved = True


    squad["players"] = current_players

    squad["score"] = round(
        current_score,
        3
    )

    return squad


best_15_squad = optimize_squad()


# ============================================================
# 14. BUILD STARTING XI FROM 15
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


def build_xi_from_squad(
    squad_players,
    formation
):

    defenders_needed = formation[0]

    midfielders_needed = formation[1]

    forwards_needed = formation[2]


    lineup = []


    # --------------------------------------------------------
    # GK
    # --------------------------------------------------------

    gks = sorted(

        [
            p

            for p in squad_players

            if p["position"] == "GK"

        ],

        key=lambda p:
        p["agent_score"],

        reverse=True

    )

    if not gks:
        return None

    lineup.append(
        gks[0]
    )


    # --------------------------------------------------------
    # DEF
    # --------------------------------------------------------

    defs = sorted(

        [
            p

            for p in squad_players

            if p["position"] == "DEF"

        ],

        key=lambda p:
        p["agent_score"],

        reverse=True

    )

    if len(defs) < defenders_needed:
        return None

    lineup.extend(
        defs[:defenders_needed]
    )


    # --------------------------------------------------------
    # MID
    # --------------------------------------------------------

    mids = sorted(

        [
            p

            for p in squad_players

            if p["position"] == "MID"

        ],

        key=lambda p:
        p["agent_score"],

        reverse=True

    )

    if len(mids) < midfielders_needed:
        return None

    lineup.extend(
        mids[:midfielders_needed]
    )


    # --------------------------------------------------------
    # FWD
    # --------------------------------------------------------

    fwds = sorted(

        [
            p

            for p in squad_players

            if p["position"] == "FWD"

        ],

        key=lambda p:
        p["agent_score"],

        reverse=True

    )

    if len(fwds) < forwards_needed:
        return None

    lineup.extend(
        fwds[:forwards_needed]
    )


    if len(lineup) != 11:
        return None


    score = sum(

        p["agent_score"]

        for p in lineup

    )


    return {

        "formation":
            formation,

        "players":
            lineup,

        "score":
            round(
                score,
                3
            )

    }


# ============================================================
# 15. FIND BEST XI
# ============================================================

model_lineups = []


if best_15_squad:

    for formation in formations:

        result = build_xi_from_squad(

            best_15_squad["players"],

            formation

        )

        if result:

            model_lineups.append(
                result
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
# 16. BENCH
# ============================================================

bench = []


if best_15_squad and best_model_lineup:

    starting_ids = {

        p["id"]

        for p in best_model_lineup[
            "players"
        ]

    }


    bench_candidates = [

        p

        for p in best_15_squad[
            "players"
        ]

        if p["id"]
        not in starting_ids

    ]


    # Bench ordered by expected usefulness
    bench_candidates.sort(

        key=lambda p:
        p["agent_score"],

        reverse=True

    )


    bench = bench_candidates


# ============================================================
# 17. CAPTAIN / VICE
# ============================================================

captain = None
vice_captain = None


if best_model_lineup:

    def captain_score(player):

        score = player[
            "agent_score"
        ]

        score += (
            player[
                "fixture_score"
            ]
            * 1.5
        )

        score += (
            player[
                "expected_goal_involvements"
            ]
            * 0.80
        )

        score += (
            player[
                "form"
            ]
            * 0.50
        )

        score += (
            player[
                "minutes"
            ]
            /
            1000
        )

        if player[
            "chance_this_round"
        ] >= 90:

            score += 1.5

        return score


    captain_candidates = sorted(

        best_model_lineup[
            "players"
        ],

        key=captain_score,

        reverse=True

    )


    if captain_candidates:

        captain = (
            captain_candidates[0]
        )


    if len(
        captain_candidates
    ) > 1:

        vice_captain = (
            captain_candidates[1]
        )


# ============================================================
# 18. PRINT FINAL SQUAD
# ============================================================

print("")
print("========================================")
print("          BEST £100M SQUAD")
print("========================================")


if best_15_squad:

    print(
        "Total Cost: £",
        best_15_squad[
            "cost"
        ]
    )

    print(
        "Money Left: £",
        best_15_squad[
            "money_left"
        ]
    )

    print(
        "Squad Score:",
        best_15_squad[
            "score"
        ]
    )

    print("")

    for player in sorted(

        best_15_squad[
            "players"
        ],

        key=lambda p:
        p["position_id"]

    ):

        print(
            player["position"],
            "|",
            player["name"],
            "|",
            player["team"],
            "| £",
            player["price"],
            "| Score:",
            player["agent_score"]
        )

else:

    print(
        "ERROR: Could not build £100M squad."
    )


# ============================================================
# 19. PRINT STARTING XI
# ============================================================

print("")
print("========================================")
print("          STARTING XI")
print("========================================")


if best_model_lineup:

    print(
        "Formation:",
        best_model_lineup[
            "formation"
        ]
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
            "| £",
            player["price"],
            "| Score:",
            player["agent_score"]
        )

else:

    print(
        "No Starting XI available."
    )


# ============================================================
# 20. PRINT BENCH
# ============================================================

print("")
print("========================================")
print("               BENCH")
print("========================================")


if bench:

    for index, player in enumerate(
        bench,
        1
    ):

        print(
            index,
            "|",
            player["position"],
            "|",
            player["name"],
            "|",
            player["team"],
            "| £",
            player["price"]
        )

else:

    print(
        "No bench available."
    )


# ============================================================
# 21. CAPTAIN OUTPUT
# ============================================================

print("")
print("========================================")
print("        CAPTAIN / VICE-CAPTAIN")
print("========================================")


if captain:

    print(
        "⭐ CAPTAIN:",
        captain["name"],
        "|",
        captain["team"],
        "| £",
        captain["price"]
    )


if vice_captain:

    print(
        "🥈 VICE-CAPTAIN:",
        vice_captain["name"],
        "|",
        vice_captain["team"],
        "| £",
        vice_captain["price"]
    )


# ============================================================
# 22. TOP PLAYERS
# ============================================================

print("")
print("========================================")
print("             TOP PLAYERS")
print("========================================")


for index, player in enumerate(

    analysed_players[:TOP_PLAYERS],

    1

):

    print(
        f"{index}. "
        f"{player['name']} | "
        f"{player['team']} | "
        f"{player['position']} | "
        f"£{player['price']} | "
        f"Score {player['agent_score']} | "
        f"Form {player['form']} | "
        f"xGI {player['expected_goal_involvements']} | "
        f"Fixture {player['fixture_score']}"
    )


# ============================================================
# 23. OUTPUT JSON
# ============================================================

output = {

    "agent": {

        "name":
            "FPL Autonomous Agent",

        "version":
            "5.0",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat()

    },

    "team_id":
        TEAM_ID,

    "target_gameweek":
        current_event,

    "budget":
        BUDGET,

    "players":
        players,

    "analysed_players":
        analysed_players,

    "fixtures":
        fixtures,

    "fpl_teams":
        teams,

    "best_15_squad":
        best_15_squad,

    "starting_xi":
        best_model_lineup,

    "bench":
        bench,

    "captain":
        captain,

    "vice_captain":
        vice_captain,

    "model_lineups":
        model_lineups

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
print("          AGENT FINISHED")
print("========================================")

print(
    "Gameweek:",
    current_event
)

print(
    "Budget: £",
    BUDGET
)

if best_15_squad:

    print(
        "Squad cost: £",
        best_15_squad[
            "cost"
        ]
    )

    print(
        "Money left: £",
        best_15_squad[
            "money_left"
        ]
    )

    print(
        "Players:",
        len(
            best_15_squad[
                "players"
            ]
        )
    )

if best_model_lineup:

    print(
        "Starting XI:",
        len(
            best_model_lineup[
                "players"
            ]
        )
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
    "Saved: fpl_data.json"
)

print("")
print("========================================")
