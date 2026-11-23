"""Срез: рассуждения агента."""
from __future__ import annotations

import statistics

from ..render import bullets, fmt_int, h1, h2, prev, table


def render(ctx, **opts) -> str:
    d = ctx.m
    top = int(opts.get("top", 8))
    sizes = [r["chars"] for r in d.reasons]
    out = [h1("Рассуждения"), ""]
    out.append(bullets([
        f"частей: {len(d.reasons)}; символов: {fmt_int(sum(sizes))}",
        (f"медиана {fmt_int(statistics.median(sizes))} / максимум {fmt_int(max(sizes))} симв. на часть"
         if sizes else "частей нет"),
    ]))
    out.append(h2(f"Топ-{top} по длине"))
    out.append(table(
        ["обмен", "симв.", "превью"],
        [(r["exchange"], fmt_int(r["chars"]), prev(r["text"], 120)) for r in d.reasons_by_size(top)],
        ["r", "r", "l"],
    ))
    silent = [e["n"] for e in d.exs if e["reasoning"] and not e["texts"]]
    out.append(h2(f"Рассуждение без пользовательского текста ({len(silent)} обменов)"))
    out.append(", ".join(str(n) for n in silent[:40]) or "-")
    out.append("")
    return "\n".join(out)
