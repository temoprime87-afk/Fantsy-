import json
import urllib.request
import urllib.error
import time
import os
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

TEAM_ID = 9623737

BASE_URL = "https://fantasy.premierleague.com/api"

TOP_PLAYERS = 30
UPCOMING_FIXTURES = 5

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36"
)


# ============================================================
# AUTHENTICATION
# ============================================================

# GitHub Secret:
# FPL_COOKIE
#
# Example value:
# pl_profile=xxxx; sessionid=xxxx; ACCESS_TOKEN=xxxx
#
# Optional:
# FPL_ACCESS_TOKEN
#
# If available, it will be sent as:
# X-API-Authorization: Bearer TOKEN

FPL_COOKIE = os.getenv("FPL_COOKIE", "").strip()
FPL_ACCESS_TOKEN = os.getenv(
    "FPL_ACCESS_TOKEN",
    ""
).strip()


# ============================================================
# API
# ============================================================

def get_json(url, authenticated=False, retries=3):

    last_error = None

    for attempt in range(retries):

        try:

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "application/json, "
                    "text/javascript, */*; q=0.01"
                ),
                "Referer":
                    "https://fantasy.premierleague.com/",
                "Origin":
                    "https://fantasy.premierleague.com",
                "X-Requested-With":
                    "XMLHttpRequest"
            }

            if authenticated:

                if FPL_COOKIE:

                    headers["Cookie"] = FPL_COOKIE

                if FPL_ACCESS_TOKEN:

                    headers[
                        "X-API-Authorization"
                    ] = (
                        "Bearer "
                        + FPL_ACCESS_TOKEN
                    )

            request = urllib.request.Request(
                url,
                headers=headers,
                method="GET"
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

                return json.loads(raw)

        except urllib.error.HTTPError as error:

            body = ""

            try:
                body = error.read().decode(
                    "utf-8",
                    errors="ignore"
                )
            except:
                pass

            last_error = (
                f"HTTP {error.code}: "
                f"{error.reason}"
            )

            if error.code == 401:

                raise RuntimeError(
                    "AUTH ERROR 401. "
                    "FPL authentication is invalid."
                )

            if error.code == 403:

                raise RuntimeError(
                    "AUTH ERROR 403. "
                    "FPL rejected authentication. "
                    "Update FPL_COOKIE."
                )

            if error.code == 404:

                raise RuntimeError(
                    f"HTTP 404: {url}"
                )

            if error.code in [
                429,
                500,
                502,
                503,
                504
            ]:

                time.sleep(
                    2 + attempt * 2
                )

                continue

            raise RuntimeError(
                f"{last_error} | "
                f"URL: {url} | "
                f"Response: {body[:300]}"
            )

        except urllib.error.URLError as error:

            last_error = (
                f"Network error: "
                f"{error.reason}"
            )

            time.sleep(
                2 + attempt * 2
            )

        except Exception as error:

            last_error = str(error)

            time.sleep(
                2 + attempt * 2
            )

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

    except:

        return default


def integer(value, default=0):

    try:

        if value is None:
            return default

        return int(value)

    except:

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
print("       FPL AUTONOMOUS AGENT v3")
print("========================================")
print("")

print(
    "Team ID:",
    TEAM_ID
)

print(
    "Authentication:",
    "AVAILABLE"
    if (
        FPL_COOKIE
        or FPL_ACCESS_TOKEN
    )
    else
    "MISSING"
)


if not FPL_COOKIE and not FPL_ACCESS_TOKEN:

    print("")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("ERROR: FPL authentication is missing.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("")
    print(
        "Add GitHub Secret: FPL_COOKIE"
    )
    print("")
    print(
        "Do NOT put your FPL password in this code."
    )

    raise RuntimeError(
        "FPL_COOKIE or FPL_ACCESS_TOKEN is required."
    )


# ============================================================
# 1. TEAM DATA
# ============================================================

print("")
print("Loading team data...")

team = get_json(
    f"{BASE_URL}/entry/{TEAM_ID}/"
)

print(
    "Team:",
    team.get(
        "name",
        "Unknown"
    )
)

print(
    "Manager:",
    team.get(
        "player_first_name",
        ""
    ),
    team.get(
        "player_last_name",
        ""
    )
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

        current_event = integer(
            event.get("id")
        )

        break


if current_event is None:

    for event in events:

        if event.get("is_next"):

            current_event = max(
                1,
                integer(
                    event.get("id")
                ) - 1
            )

            break


if current_event is None:

    current_event = integer(
        team.get(
            "current_event"
        )
    )


if current_event <= 0:

    current_event = 1


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

        "event":
            event,

        "opponent":
            away_team,

        "home":
            True,

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

        "event":
            event,

        "opponent":
            home_team,

        "home":
            False,

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
# 8. REAL SQUAD
# ============================================================

current_picks = None
squad_error = None
current_player_ids = set()

print("")
print("========================================")
print("          LOADING REAL SQUAD")
print("========================================")


# ------------------------------------------------------------
# FIRST METHOD: /my-team/{TEAM_ID}/
# ------------------------------------------------------------

my_team_url = (
    f"{BASE_URL}/my-team/"
    f"{TEAM_ID}/"
)

try:

    my_team_data = get_json(
        my_team_url,
        authenticated=True
    )

    picks_from_my_team = my_team_data.get(
        "picks",
        []
    )

    if picks_from_my_team:

        current_picks = {
            "picks":
                picks_from_my_team,

            "source":
                "my-team"
        }

        print(
            "REAL SQUAD LOADED:",
            len(
                picks_from_my_team
            ),
            "players"
        )

        for pick in picks_from_my_team:

            element = pick.get(
                "element"
            )

            if element:

                current_player_ids.add(
                    integer(element)
                )

    else:

        print(
            "my-team returned no picks."
        )

except Exception as error:

    squad_error = str(error)

    print(
        "my-team failed:",
        squad_error
    )


# ------------------------------------------------------------
# SECOND METHOD: EVENT PICKS
# ------------------------------------------------------------

if not current_player_ids:

    print("")
    print(
        "Trying event picks endpoint..."
    )

    picks_url = (
        f"{BASE_URL}/entry/"
        f"{TEAM_ID}/event/"
        f"{current_event}/picks/"
    )

    try:

        event_picks = get_json(
            picks_url,
            authenticated=True
        )

        picks_list = event_picks.get(
            "picks",
            []
        )

        if picks_list:

            current_picks = event_picks

            print(
                "REAL SQUAD LOADED:",
                len(picks_list),
                "players"
            )

            for pick in picks_list:

                element = pick.get(
                    "element"
                )

                if element:

                    current_player_ids.add(
                        integer(element)
                    )

        else:

            print(
                "Event picks returned empty."
            )

    except Exception as error:

        squad_error = str(error)

        print(
            "Event picks failed:",
            squad_error
        )


# ============================================================
# 9. HISTORY
# ============================================================

print("")
print("Loading team history...")

history = None
history_error = None

try:

    history = get_json(
        f"{BASE_URL}/entry/"
        f"{TEAM_ID}/history/"
    )

    print(
        "History loaded successfully."
    )

except Exception as error:

    history_error = str(error)

    print(
        "History unavailable:",
        history_error
    )


# ============================================================
# 10. BUDGET
# ============================================================

team_value = None
bank = None


# ------------------------------------------------------------
# ENTRY DATA
# ------------------------------------------------------------

if team.get(
    "last_deadline_value"
) is not None:

    team_value = money(
        team.get(
            "last_deadline_value"
        )
    )


if team.get(
    "last_deadline_bank"
) is not None:

    bank = money(
        team.get(
            "last_deadline_bank"
        )
    )


# ------------------------------------------------------------
# MY TEAM DATA
# ------------------------------------------------------------

if current_picks:

    transfers = current_picks.get(
        "transfers",
        {}
    )

    if isinstance(
        transfers,
        dict
    ):

        if bank is None:

            if transfers.get(
                "bank"
            ) is not None:

                bank = money(
                    transfers.get(
                        "bank"
                    )
                )


# ------------------------------------------------------------
# HISTORY FALLBACK
# ------------------------------------------------------------

if history:

    current_history = history.get(
        "current",
        []
    )

    if current_history:

        latest = current_history[-1]

        if team_value is None:

            if latest.get(
                "value"
            ) is not None:

                team_value = money(
                    latest.get(
                        "value"
                    )
                )

        if bank is None:

            if latest.get(
                "bank"
            ) is not None:

                bank = money(
                    latest.get(
                        "bank"
                    )
                )


print("")
print("========================================")
print("                BUDGET")
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
# 11. PLAYER ANALYSIS
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
        player.get(
            "now_cost"
        )
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

    xgi = (
        expected_goals
        +
        expected_assists
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
    # UPCOMING FIXTURES
    # --------------------------------------------------------

    upcoming = []

    for fixture in fixture_map.get(
        team_id,
        []
    ):

        fixture_event = integer(
            fixture.get(
                "event"
            )
        )

        if fixture_event <= current_event:

            continue

        upcoming.append(
            fixture
        )

    upcoming.sort(
        key=lambda x:
        integer(
            x.get("event")
        )
    )

    upcoming = upcoming[
        :UPCOMING_FIXTURES
    ]

    difficulty_values = [

        number(
            f.get(
                "difficulty"
            ),
            3
        )

        for f in upcoming
    ]

    if difficulty_values:

        average_difficulty = (
            sum(
                difficulty_values
            )
            /
            len(
                difficulty_values
            )
        )

    else:

        average_difficulty = 3

    fixture_score = clamp(
        6 - average_difficulty,
        0,
        5
    )

    # --------------------------------------------------------
    # SCORES
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

    if position == "FWD":

        attack_weight = 1.50
        fixture_weight = 0.90

    elif position == "MID":

        attack_weight = 1.35
        fixture_weight = 0.90

    elif position == "DEF":

        attack_weight = 0.75
        fixture_weight = 1.00

    else:

        attack_weight = 0.40
        fixture_weight = 1.00

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

    )

    if chance_current < 50:

        score *= 0.40

    elif chance_current < 75:

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
            price,

        "points":
            int(points),

        "form":
            round(form, 2),

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
# 12. SORT
# ============================================================

analysed_players.sort(

    key=lambda x:
    x["agent_score"],

    reverse=True

)


# ============================================================
# 13. TOP PLAYERS
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
# 14. POSITION FILTER
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
# 15. BUILD XI
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
    lineup,
    candidate
):

    count = sum(

        1

        for player in lineup

        if player["team_id"]
        ==
        candidate["team_id"]

    )

    return count < 3


def select_position(
    lineup,
    position,
    needed
):

    selected = 0

    candidates = players_by_position(
        position
    )

    for player in candidates:

        if selected >= needed:

            break

        if not team_count_ok(
            lineup,
            player
        ):

            continue

        if player[
            "chance_this_round"
        ] < 50:

            continue

        lineup.append(
            player
        )

        selected += 1

    return selected == needed


def build_lineup(
    formation
):

    defenders_needed = formation[0]
    midfielders_needed = formation[1]
    forwards_needed = formation[2]

    lineup = []

    if not select_position(
        lineup,
        "GK",
        1
    ):

        return None

    if not select_position(
        lineup,
        "DEF",
        defenders_needed
    ):

        return None

    if not select_position(
        lineup,
        "MID",
        midfielders_needed
    ):

        return None

    if not select_position(
        lineup,
        "FWD",
        forwards_needed
    ):

        return None

    if len(lineup) != 11:

        return None

    cost = sum(
        p["price"]
        for p in lineup
    )

    score = sum(
        p["agent_score"]
        for p in lineup
    )

    return {

        "formation":
            formation,

        "players":
            lineup,

        "cost":
            round(
                cost,
                1
            ),

        "score":
            round(
                score,
                3
            )

    }


model_lineups = []

for formation in formations:

    result = build_lineup(
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
# 16. CAPTAIN
# ============================================================

captain = None
vice_captain = None


if best_model_lineup:

    captain_candidates = sorted(

        best_model_lineup[
            "players"
        ],

        key=lambda p: (

            p["agent_score"]

            +
            p["fixture_score"]

            +
            p[
                "expected_goal_involvements"
            ] * 0.50

        ),

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
# 17. MODEL XI
# ============================================================

print("")
print("========================================")
print("           MODEL STARTING XI")
print("========================================")


if best_model_lineup:

    print(
        "Formation:",
        best_model_lineup[
            "formation"
        ]
    )

    print(
        "Cost:",
        best_model_lineup[
            "cost"
        ]
    )

    print(
        "Score:",
        best_model_lineup[
            "score"
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
            "| Score:",
            player["agent_score"]
        )

else:

    print(
        "Could not build model XI."
    )


# ============================================================
# 18. CAPTAIN
# ============================================================

print("")
print("========================================")
print("           CAPTAIN ANALYSIS")
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
# 19. SQUAD STATUS
# ============================================================

print("")
print("========================================")
print("             SQUAD STATUS")
print("========================================")


if current_player_ids:

    print(
        "REAL SQUAD:",
        len(
            current_player_ids
        ),
        "players"
    )

    print(
        "Authentication worked."
    )

else:

    print(
        "REAL SQUAD: NOT AVAILABLE"
    )

    print(
        "Reason:",
        squad_error
    )


# ============================================================
# 20. TRANSFER ANALYSIS
# ============================================================

print("")
print("========================================")
print("          TRANSFER ANALYSIS")
print("========================================")


if current_player_ids:

    print(
        "Using REAL squad."
    )

    transfer_candidates = [

        p

        for p in analysed_players

        if p["id"]
        not in current_player_ids

    ]

else:

    print(
        "Real squad unavailable."
    )

    print(
        "Using general targets."
    )

    transfer_candidates = (
        analysed_players.copy()
    )


transfer_candidates.sort(

    key=lambda p: (

        p["value_score"] * 0.65

        +
        p["agent_score"] * 0.35

    ),

    reverse=True

)


print("")
print("TRANSFER TARGETS")
print("----------------------------------------")


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
        f"Value {player['value_score']} | "
        f"Price {player['price']}"
    )


# ============================================================
# 21. REAL SQUAD DETAILS
# ============================================================

real_squad_players = []

if current_player_ids:

    player_lookup = {

        p["id"]: p

        for p in analysed_players

    }

    for player_id in current_player_ids:

        if player_id in player_lookup:

            real_squad_players.append(
                player_lookup[
                    player_id
                ]
            )


real_squad_players.sort(

    key=lambda p:
    p["position_id"]

)


# ============================================================
# 22. CHIPS
# ============================================================

chips = {
    "history": []
}

print("")
print("Loading chip history...")

if history:

    chips["history"] = history.get(
        "chips",
        []
    )

print(
    "Chips found:",
    len(
        chips["history"]
    )
)


# ============================================================
# 23. BUDGET DATA
# ============================================================

budget_data = {

    "team_value":
        team_value,

    "bank":
        bank,

    "raw_team_value":
        team.get(
            "last_deadline_value"
        ),

    "raw_bank":
        team.get(
            "last_deadline_bank"
        )

}


# ============================================================
# 24. FINAL OUTPUT
# ============================================================

output = {

    "agent": {

        "name":
            "FPL Autonomous Agent",

        "version":
            "3.0",

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

    "budget":
        budget_data,

    "real_squad_available":
        bool(
            current_player_ids
        ),

    "squad_error":
        squad_error,

    "history_error":
        history_error,

    "current_picks":
        current_picks,

    "real_squad_players":
        real_squad_players,

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

    "chips":
        chips

}


# ============================================================
# 25. SAVE
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
# 26. FINAL STATUS
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
    len(
        analysed_players
    )
)

print(
    "Real squad:",
    bool(
        current_player_ids
    )
)

print(
    "Squad players:",
    len(
        current_player_ids
    )
)

print(
    "Team value:",
    team_value
)

print(
    "Bank:",
    bank
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
print("========================================")
print("       AGENT CONNECTED SUCCESSFULLY")
print("========================================")
