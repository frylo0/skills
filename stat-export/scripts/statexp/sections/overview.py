"""Срез: обзор сессии."""
from __future__ import annotations

import collections
import statistics

from ..model import iter_assistant, span
from ..render import bullets, fmt_dur, fmt_int, h1, h2, table


def render(ctx, **opts) -> str:
    m, d = ctx.meta, ctx.m
    t, tm = m["tokens"], m["time"]
    reason_chars = sum(r["chars"] for r in d.reasons)
    text_chars = sum(x["chars"] for x in d.texts)
    cache_total = t["cache_read"] + t["cache_write"]
    types = collections.Counter()
    agents = collections.Counter()
    finishes = collections.Counter()
    for ex in d.exs:
        types.update(ev["type"] for ev in ex["events"])
        finishes.update(ex["finishes"])
    for _, am in iter_assistant(ctx.sess):
        agents[am["agent"] or "-"] += 1

    out = [h1("Обзор сессии")]
    out.append(bullets([
        f"**Заголовок:** {m['title']}",
        f"**ID:** `{m['id']}`",
        f"**Проект:** `{m['project']}`",
        f"**Агент / модель:** {m['agent']} / {m['model']} ({m['variant']})",
        f"**Итог:** {m['outcome']}",
        f"**Стоимость:** ${m['cost']:.4f}",
        f"**Сообщений:** {fmt_int(m['message_count'])}; обменов: {len(d.exs)}",
        f"**Время:** {fmt_dur(span(tm.get('created'), tm.get('updated')))} всего, "
        f"busy {fmt_dur(span(tm.get('created'), tm.get('busy')))}, "
        f"idle {fmt_dur(span(tm.get('busy'), tm.get('idle')))}",
    ]))
    out.append(h2("Токены"))
    out.append(table(["тип", "значение"], [
        ("input", fmt_int(t["input"])), ("output", fmt_int(t["output"])),
        ("reasoning", fmt_int(t["reasoning"])), ("cache read", fmt_int(t["cache_read"])),
        ("cache write", fmt_int(t["cache_write"])),
    ], ["l", "r"]))
    out.append(bullets([
        f"reasoning / output: {t['reasoning'] / t['output']:.2f}x" if t["output"] else "reasoning / output: -",
        f"доля cache read: {100 * t['cache_read'] / cache_total:.1f}%" if cache_total else "доля cache read: -",
    ]))
    out.append(h2("Сообщения"))
    out.append(table(["тип", "кол-во"], types.most_common(), ["l", "r"]))
    out.append(bullets([
        f"агенты (ассистент-сообщения): {', '.join(f'{k} {v}' for k, v in agents.most_common())}",
        f"finish: {', '.join(f'{k} {v}' for k, v in finishes.most_common())}",
    ]))
    out.append(h2("Инструменты"))
    out.append(bullets([
        f"всего вызовов: {len(d.tools)}; " + ", ".join(f"{k} {v}" for k, v in d.by_status.most_common()),
        "по имени: " + ", ".join(f"{k} {v}" for k, v in d.by_name.most_common()),
    ]))
    out.append(h2("Рассуждения и текст"))
    out.append(bullets([
        f"частей рассуждения: {len(d.reasons)}; символов: {fmt_int(reason_chars)}; токенов: {fmt_int(t['reasoning'])}",
        f"текстовых частей: {len(d.texts)}; символов: {fmt_int(text_chars)}",
    ]))
    if d.reasons:
        sizes = [r["chars"] for r in d.reasons]
        out.append(bullets([
            f"размер части: медиана {fmt_int(statistics.median(sizes))}, "
            f"среднее {fmt_int(statistics.mean(sizes))}, максимум {fmt_int(max(sizes))}"
        ]))
    return "\n".join(out)
