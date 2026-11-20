"""Render the profile's current calendar year using GitHub's contribution data."""

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen


MONTHS = "ene feb mar abr may jun jul ago sep oct nov dic".split()
LEVELS = ("NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE")
COLORS = ("#193341", "#185b6c", "#168b99", "#30c6c6", "#acfff1")
ASSETS = Path(__file__).resolve().parents[1] / "assets"


def fetch_days(now):
    start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    query = """
      query($login:String!, $from:DateTime!, $to:DateTime!) {
        user(login:$login) {
          contributionsCollection(from:$from, to:$to) {
            contributionCalendar {
              weeks { contributionDays { date contributionCount contributionLevel } }
            }
          }
        }
      }"""
    variables = {"login": os.environ["PROFILE_USER"], "from": start.isoformat(), "to": now.isoformat()}
    request = Request("https://api.github.com/graphql",
                      data=json.dumps({"query": query, "variables": variables}).encode(),
                      headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                               "Content-Type": "application/json", "User-Agent": "haluz-profile"})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return {date.fromisoformat(day["date"]): (day["contributionCount"], LEVELS.index(day["contributionLevel"]))
            for week in calendar["weeks"] for day in week["contributionDays"]}


def calendar_svg(days, today, compact):
    year = today.year
    first = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    # Index every elapsed day explicitly. Missing API data must never appear as zero activity.
    total = sum(days[first + timedelta(days=i)][0] for i in range((today - first).days + 1))
    width, height = (412, 342) if compact else (800, 216)
    spans = [(first, date(year, 7, 1)), (date(year, 7, 1), end)] if compact else [(first, end)]
    pitch = 12 if compact else 13
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{total} contribuciones en {year}</title>',
             f'<desc id="desc">Actividad pública del 1 de enero al {today.day} de {MONTHS[today.month - 1]}. Cada celda representa un día.</desc>',
             '<style>@media (prefers-reduced-motion: no-preference) {'
             '.sweep { animation: scan 7s linear infinite }'
             '.active-day { animation: highlight 9s ease-in-out infinite; animation-delay:var(--phase) }'
             '@keyframes highlight { 0%,18%,100% { stroke-opacity:0 } 8% { stroke-opacity:.85 } }'
             '@keyframes scan { to { stroke-dashoffset:-100 } } }</style>',
             f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="3" fill="#08161e" stroke="#315561"/>',
             '<path d="M1 1h98l8 5h30" fill="none" stroke="#59dce4" stroke-width="2"/>',
             f'<path d="M18 48H{width-18}" stroke="#25434d"/>',
             f'<path class="sweep" d="M18 48H{width-18}" pathLength="100" stroke="#6ce0dc" stroke-width="2" stroke-dasharray="7 93"/>',
             '<g font-family="Segoe UI,Arial,sans-serif">',
             f'<text x="18" y="36" fill="#e7f9fa" font-weight="700" font-size="22">Actividad · {year}</text>',
             f'<text x="{width-17}" y="35" text-anchor="end" fill="#8bdedc" font-size="15">{total} contribuciones</text></g>',
             '<g font-family="Consolas,monospace" font-size="11" fill="#afd0d5">']
    for index, (begin, stop) in enumerate(spans):
        top = 74 + index * 133
        sunday = begin - timedelta(days=(begin.weekday() + 1) % 7)
        day = begin
        for label, row in (("Lu", 1), ("Mi", 3), ("Vi", 5)):
            parts.append(f'<text x="16" y="{top + row*pitch + 8}">{label}</text>')
        while day < stop:
            column, row = divmod((day - sunday).days, 7)
            x, y = 43 + column*pitch, top + row*pitch
            if day.day == 1:
                parts.append(f'<text x="{x}" y="{top-7}">{MONTHS[day.month-1]}</text>')
            if day <= today:
                count, level = days[day]
                highlight = ''
                if count:
                    phase = (column * 0.14 + row * 0.05) - 9
                    highlight = f' class="active-day" stroke="#baffef" stroke-opacity="0" style="--phase:{phase:.2f}s"'
                parts.append(f'<rect x="{x}" y="{y}" width="{pitch-3}" height="{pitch-3}" rx="2" fill="{COLORS[level]}"{highlight}><title>{day} · {count}</title></rect>')
                if day == today:
                    parts.append(f'<rect id="today" x="{x-1}" y="{y-1}" width="{pitch-1}" height="{pitch-1}" rx="2.5" fill="none" stroke="#ffca70" stroke-width="1.5"><title>Hoy · {day}</title></rect>')
            else:
                parts.append(f'<circle cx="{x+4}" cy="{y+4}" r="1.4" fill="#37505c"/>')
            day += timedelta(days=1)
    foot = height - 16
    parts.append(f'<text x="17" y="{foot}">Al {today.day:02d} {MONTHS[today.month-1]} {year}</text>')
    parts.append(f'<text x="{width-142}" y="{foot}">Menos</text>')
    for i, color in enumerate(COLORS):
        parts.append(f'<rect x="{width-102+i*12}" y="{foot-8}" width="9" height="9" rx="2" fill="{color}"/>')
    parts.extend((f'<text x="{width-34}" y="{foot}">Más</text>', '</g></svg>'))
    return "\n".join(parts) + "\n"


def write_calendars(days, today):
    for name, compact in (("actividad.svg", False), ("actividad-movil.svg", True)):
        (ASSETS / name).write_text(calendar_svg(days, today, compact), encoding="utf-8")


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    write_calendars(fetch_days(now), now.date())
