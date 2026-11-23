"""Срез: причинные цепочки — что спровоцировало действие."""
from __future__ import annotations

from ..model import prev, user_text
from ..render import bullets, fmt_dur, h1, table


def _chain(ex) -> dict:
    decision = ""
    for t in ex["texts"]:
        if t["text"].strip():
            decision = t["text"]
            break
    if not decision and ex["reasoning"]:
        decision = ex["reasoning"][0]["text"]
    calls = []
    for t in ex["tools"]:
        calls.append(f"{t['name']}{'!' if t['status'] == 'error' else ''}")
    last = ex["texts"][-1]["text"] if ex["texts"] else ""
    return {
        "n": ex["n"], "request": prev(user_text(ex), 170),
        "decision": prev(decision, 200), "calls": " ".join(calls[:14]) or "-",
        "errors": sum(1 for t in ex["tools"] if t["status"] == "error"),
        "finish": ",".join(ex["finishes"]) or "-", "result": prev(last, 170),
        "duration": fmt_dur(ex["duration_ms"]),
    }


def render(ctx, **opts) -> str:
    d = ctx.m
    flagged_only = bool(opts.get("flagged", False))
    top = int(opts.get("top", 10))
    exs = d.flagged() if flagged_only else d.exs
    if flagged_only:
        exs = sorted(exs, key=lambda e: (0 if "ERR" in d.flags.get(e["n"], []) else 1, e["n"]))
    chosen = [_chain(e) for e in exs[:top]]
    out = [h1("Причинные цепочки"), ""]
    out.append(bullets([
        "Для каждого обмена: запрос пользователя → решение агента → вызовы → результат.",
        "`!` после имени инструмента = ошибка. `chains --flagged` — только обмены с флагами.",
    ]))
    out.append(table(
        ["#", "dur", "запрос → решение", "инструменты", "ош", "finish / результат"],
        [(c["n"], c["duration"], f"{c['request']}\n→ {c['decision']}", c["calls"],
          c["errors"], f"{c['finish']} / {c['result']}") for c in chosen],
        ["r", "l", "l", "l", "r", "l"],
    ))
    out.append("")
    return "\n".join(out)
