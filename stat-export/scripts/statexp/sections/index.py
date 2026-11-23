"""Срез: таблица обменов — навигация по сессии."""
from __future__ import annotations

from ..metrics import FLAG_HELP
from ..model import burned, prev, user_text
from ..render import fmt_clock, fmt_dur, fmt_int, h1, bullets, table


def render(ctx, **opts) -> str:
    d = ctx.m
    out = [h1("Индекс обменов")]
    out.append(bullets([
        "Флаги: " + "; ".join(f"{k} — {v}" for k, v in FLAG_HELP.items()),
    ]))
    rows = []
    for ex in d.exs:
        tk = ex["tokens"]
        rows.append((
            ex["n"], fmt_clock(ex["started"]), len(ex["assistant"]), len(ex["tools"]),
            f"{fmt_int(tk['input'])}/{fmt_int(tk['output'])}/{fmt_int(tk['reasoning'])}",
            f"{ex['cost']:.3f}", fmt_dur(ex["duration_ms"]),
            ",".join(d.flags.get(ex["n"], [])) or "-",
            prev(user_text(ex), 55),
        ))
    out.append(table(
        ["#", "время", "асс", "инстр", "in/out/r", "$", "dur", "флаги", "запрос"], rows,
        ["r", "l", "r", "r", "l", "r", "l", "l", "l"],
    ))
    out.append(bullets([
        f"Медиана burnt-токенов на обмен: {fmt_int(d.med_burn)}; максимум: {fmt_int(d.max_burn)}.",
        f"Обменов с флагами: {len(d.flagged())} из {len(d.exs)}.",
    ]))
    return "\n".join(out)
