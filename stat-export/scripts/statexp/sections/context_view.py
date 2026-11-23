"""Срез: куда ушёл бюджет контекста — более мелкий масштаб, чем index."""
from __future__ import annotations

import collections

from ..model import burned, iter_assistant, prev, user_text
from ..render import bullets, fmt_int, h1, h2, table


def render(ctx, **opts) -> str:
    d, m = ctx.m, ctx.meta
    top = int(opts.get("top", 10))
    total = burned(m["tokens"]) or 1
    out = [h1("Бюджет контекста"), ""]
    out.append(bullets([
        f"burnt-токенов всего: {fmt_int(total)}; самая дорогая строка ниже — не всегда самая длинная.",
        "Показываем отдельно сообщения, рассуждения, выводы инструментов и запросы: единицы разные.",
    ]))

    out.append(h2(f"Топ-{top} ассистентских сообщений по токенам"))
    out.append(table(
        ["#", "агент", "in/out/r", "инстр", "finish", "что делал"],
        [(h["exchange"], h["agent"] or "-",
          f"{fmt_int(h['detail']['input'])}/{fmt_int(h['detail']['output'])}/{fmt_int(h['detail']['reasoning'])}",
          h["tools"], h["finish"] or "-", h["preview"]) for h in d.hotspots[:top]],
        ["r", "l", "l", "r", "l", "l"],
    ))

    out.append(h2(f"Топ-{top} рассуждений по размеру"))
    out.append(table(
        ["#", "симв.", "доля от reasoning", "превью"],
        [(r["exchange"], fmt_int(r["chars"]),
          f"{100 * r['chars'] / max(1, sum(x['chars'] for x in d.reasons)):.1f}%", prev(r["text"], 110))
         for r in d.reasons_by_size(top)],
        ["r", "r", "r", "l"],
    ))

    out.append(h2(f"Топ-{top} выводов инструментов"))
    out.append(table(
        ["#", "инструмент", "симв.", "превью"],
        [(t["exchange"], t["name"], fmt_int(t["out_chars"]), prev(t["out_text"], 110))
         for t in d.big_outputs[:top]],
        ["r", "l", "r", "l"],
    ))

    users = sorted(ctx.sess["exchanges"], key=lambda e: -len(user_text(e)))[:top]
    out.append(h2(f"Топ-{top} запросов пользователя по размеру"))
    out.append(table(
        ["#", "симв.", "превью"],
        [(e["n"], fmt_int(len(user_text(e))), prev(user_text(e), 130)) for e in users],
        ["r", "r", "l"],
    ))

    by_agent = collections.Counter()
    for _, am in iter_assistant(ctx.sess):
        by_agent[am["agent"] or "-"] += burned(am["tokens"])
    out.append(h2("Токены по роли/агенту"))
    out.append(table(
        ["агент", "burnt", "доля"],
        [(a, fmt_int(v), f"{100 * v / total:.1f}%") for a, v in by_agent.most_common()],
        ["l", "r", "r"],
    ))
    out.append("")
    return "\n".join(out)
