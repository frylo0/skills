"""Срез: поиск по всем текстовым слоям обмена."""
from __future__ import annotations

from ..model import jdump, prev
from ..render import fmt_clock, h1


def render(ctx, **opts) -> str:
    q = str(opts.get("query", "")).lower()
    limit = int(opts.get("limit", 30))
    out = [h1(f"Поиск: `{q}`"), ""]
    hits = 0
    for ex in ctx.m.exs:
        found = []
        for u in ex["user"]:
            if q in (u.get("text") or "").lower():
                found.append(("user", prev(u["text"], 180)))
        for r in ex["reasoning"]:
            if q in r["text"].lower():
                found.append(("reasoning", prev(r["text"], 180)))
        for t in ex["texts"]:
            if q in t["text"].lower():
                found.append(("text", prev(t["text"], 180)))
        for t in ex["tools"]:
            if q in jdump(t["input"]).lower():
                found.append(("tool-in", prev(t["input_preview"], 180)))
            if q in (t["out_text"] or "").lower():
                found.append(("tool-out", prev(t["out_text"], 180)))
        if found:
            hits += 1
            out.append(f"- обмен {ex['n']} ({fmt_clock(ex['started'])}): "
                       + "; ".join(f"{k}: {v}" for k, v in found[:4]))
            if hits >= limit:
                break
    if not hits:
        out.append("Совпадений нет.")
    out.append("")
    return "\n".join(out)
