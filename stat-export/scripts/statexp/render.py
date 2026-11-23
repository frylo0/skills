"""Единые правила форматирования markdown для всех срезов (DRY)."""
from __future__ import annotations

from datetime import datetime, timezone

from .model import clean, jdump, ms, prev  # re-export: срезы импортируют fmt отсюда

__all__ = ["h1", "h2", "para", "bullets", "table", "code", "fmt_int", "fmt_dur",
           "fmt_clock", "prev", "clean", "jdump"]


def h1(title: str) -> str:
    return f"# {title}\n"


def h2(title: str) -> str:
    return f"\n## {title}\n"


def para(text: str) -> str:
    return text + "\n"


def bullets(items) -> str:
    return "\n".join(f"- {i}" for i in items) + "\n"


def table(headers, rows, aligns=None) -> str:
    """aligns: список 'l'/'r'/'c' по числу колонок."""
    aligns = aligns or ["l"] * len(headers)
    mark = {"l": "---", "r": "---:", "c": ":---:"}
    out = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join(mark[a] for a in aligns) + " |",
    ]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out) + "\n"


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def fmt_dur(d) -> str:
    if not d:
        return "-"
    s = d / 1000
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.1f}h"


def fmt_clock(t) -> str:
    t = ms(t)
    if not t:
        return "--:--"
    return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%H:%M")


def code(text: str) -> str:
    return f"```sh\n{text}\n```\n"
