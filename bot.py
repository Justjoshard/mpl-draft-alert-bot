
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = os.environ["PANDASCORE_API_KEY"]
SGT = ZoneInfo("Asia/Singapore")

URL = "https://api.pandascore.co/mlbb/matches/upcoming"


def get_upcoming_matches():
    all_matches = []

    for page in range(1, 11):
        response = requests.get(
            URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Accept": "application/json"
            },
            params={
                "page": page,
                "per_page": 100
            },
            timeout=30
        )

        response.raise_for_status()
        matches = response.json()

        if not matches:
            break

        all_matches.extend(matches)

        if len(matches) < 100:
            break

    return all_matches


def parse_date(value):
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(SGT)


def main():
    matches = get_upcoming_matches()
    mpl_matches = []

    for match in matches:
        league = match.get("league") or {}
        league_name = league.get("name", "")

        if "MPL" not in league_name.upper():
            continue

        start = parse_date(match.get("scheduled_at"))

        if not start:
            continue

        opponents = match.get("opponents") or []

        teams = [
            item.get("opponent", {}).get("name", "TBD")
            for item in opponents
        ]

        team1 = teams[0] if len(teams) > 0 else "TBD"
        team2 = teams[1] if len(teams) > 1 else "TBD"

        mpl_matches.append({
            "league": league_name,
            "team1": team1,
            "team2": team2,
            "start": start
        })

    mpl_matches.sort(key=lambda m: m["start"])

    print(f"Found {len(mpl_matches)} upcoming MPL matches")

    for match in mpl_matches:
        print(
            f"{match['league']} | "
            f"{match['team1']} vs {match['team2']} | "
            f"{match['start']:%d %b %Y %I:%M %p} SGT"
        )


if __name__ == "__main__":
    main()
