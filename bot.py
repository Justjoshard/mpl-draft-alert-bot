
import os
import json
import random
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict

SGT = ZoneInfo("Asia/Singapore")
NOW = datetime.now(timezone.utc)
LOCAL_NOW = NOW.astimezone(SGT)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PANDA_KEY = os.environ["PANDASCORE_API_KEY"]
GH_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]

PANDA_URL = "https://api.pandascore.co/mlbb/matches/upcoming"
GH_URL = f"https://api.github.com/repos/{REPO}"
STATE_TITLE = "MPLMMbot notification state"

GREETINGS = [
    "Good morning, handsome. The sun is out, but you're still the hottest thing around. ☀️",
    "Rise and shine, sayang. Your favourite MLBB secretary is here. 💋",
    "Wakey wakey, pretty boy. Even the enemy jungler isn't chasing you as hard as I am. 😘",
    "Morning, king. Hope your day is as clean as a perfect Lord steal. 👑",
    "Good morning, leng zai. Today's forecast: 100% chance of you looking fine. ❤️",
    "Oi handsome, wake up lah. The Land of Dawn needs its favourite analyst. 😭",
    "Good morning, sweetheart. Even the turtle spawned earlier than you today. 🐢"
]

COMPLIMENTS = [
    "Hope your predictions hit today, handsome. But even if they don't, you're still a 10/10. 💕",
    "Win or lose, at least you woke up looking this fine. 😘",
    "May your predictions hit harder than a fed Aldous. 💪",
    "Remember to drink water, handsome. Can't have my favourite MPL analyst dehydrated. 💧",
    "If nobody told you today, you're looking extra handsome. Have a good day, king. ❤️",
    "Your smile has a higher win rate than solo queue. Trust me. 💋",
    "May your bets be lucky and your teammates have functioning brains. 😭"
]


def github_request(method, path, **kwargs):
    response = requests.request(
        method,
        f"{GH_URL}{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        timeout=30,
        **kwargs
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def load_state():
    issues = github_request(
        "GET",
        "/issues",
        params={"state": "open", "per_page": 100}
    )

    for issue in issues:
        if issue["title"] == STATE_TITLE:
            state = json.loads(issue["body"] or "{}")
            return issue["number"], state

    issue = github_request(
        "POST",
        "/issues",
        json={
            "title": STATE_TITLE,
            "body": "{}"
        }
    )
    return issue["number"], {}


def save_state(issue_number, state):
    github_request(
        "PATCH",
        f"/issues/{issue_number}",
        json={"body": json.dumps(state, indent=2)}
    )


def get_matches():
    all_matches = []

    for page in range(1, 11):
        response = requests.get(
            PANDA_URL,
            headers={
                "Authorization": f"Bearer {PANDA_KEY}",
                "Accept": "application/json"
            },
            params={
                "page": page,
                "per_page": 100
            },
            timeout=30
        )
        response.raise_for_status()
        batch = response.json()

        if not isinstance(batch, list):
            raise ValueError("Unexpected PandaScore response")

        all_matches.extend(batch)

        if len(batch) < 100:
            break

    results = []

    for match in all_matches:
        league = (match.get("league") or {}).get("name") or ""

        if "MPL" not in league.upper():
            continue

        scheduled = match.get("scheduled_at")

        if not scheduled:
            continue

        start = datetime.fromisoformat(
            scheduled.replace("Z", "+00:00")
        )

        opponents = match.get("opponents") or []
        teams = []

        for item in opponents:
            team = item.get("opponent") or {}
            teams.append(team.get("name") or "TBD")

        results.append({
            "id": str(match["id"]),
            "league": league,
            "team1": teams[0] if len(teams) > 0 else "TBD",
            "team2": teams[1] if len(teams) > 1 else "TBD",
            "start": start
        })

    return sorted(results, key=lambda m: m["start"])


def send_message(text):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=30
    )
    response.raise_for_status()

    if not response.json().get("ok"):
        raise RuntimeError("Telegram rejected the message")

    print("Telegram notification sent")


def daily_message(matches):
    today = LOCAL_NOW.date()

    todays_matches = [
        m for m in matches
        if m["start"].astimezone(SGT).date() == today
    ]

    grouped = defaultdict(list)

    for match in todays_matches:
        grouped[match["league"]].append(match)

    lines = [
        "☀️ " + random.choice(GREETINGS),
        "",
        "🎮 TODAY'S MPL MATCHES",
        f"📅 {today:%d %B %Y}",
        "🕒 All times Singapore time",
        ""
    ]

    if not todays_matches:
        lines.append(
            "No MPL matches scheduled today, handsome. "
            "Go touch some grass, respectfully. 🌱"
        )
        lines.append("")
    else:
        for league, games in sorted(grouped.items()):
            lines.append(f"🏆 {league}")

            for match in games:
                time = match["start"].astimezone(SGT)
                lines.append(
                    f"• {time:%I:%M %p} — "
                    f"{match['team1']} vs {match['team2']}"
                )

            lines.append("")

    lines.extend([
        "💌 YOUR DAILY COMPLIMENT",
        random.choice(COMPLIMENTS)
    ])

    return "\n".join(lines)


def pregame_message(match):
    start = match["start"].astimezone(SGT)

    return (
        "🚨 MPL MATCH STARTING SOON!\n\n"
        f"🏆 {match['league']}\n"
        f"⚔️ {match['team1']} vs {match['team2']}\n"
        f"⏰ {start:%I:%M %p} SGT\n\n"
        "🎮 Scheduled start is approaching!\n"
        "Good luck with your predictions, handsome. ❤️"
    )


def main():
    issue_number, state = load_state()

    # Keep only recent alert history.
    cutoff = (NOW - timedelta(days=7)).isoformat()
    state = {
        key: value
        for key, value in state.items()
        if isinstance(value, str) and value >= cutoff
    }

    matches = get_matches()
    print(f"Found {len(matches)} upcoming MPL matches")

    changed = False
    today = LOCAL_NOW.date().isoformat()

    # Daily greeting: first successful run between 8:00 and 8:30.
    daily_key = f"daily:{today}"

    if (
        LOCAL_NOW.hour == 8
        and LOCAL_NOW.minute < 30
        and daily_key not in state
    ):
        send_message(daily_message(matches))
        state[daily_key] = NOW.isoformat()
        changed = True
        save_state(issue_number, state)

    # Pregame reminder: scheduled start is 0 to 10 minutes away.
    for match in matches:
        seconds_until = (match["start"] - NOW).total_seconds()
        key = f"pregame:{match['id']}:{match['start'].isoformat()}"

        if 0 < seconds_until <= 600 and key not in state:
            send_message(pregame_message(match))
            state[key] = NOW.isoformat()
            changed = True
            save_state(issue_number, state)

    if not changed:
        print("No notifications needed")


if __name__ == "__main__":
    main()
