"""Срез: трение — правки пользователя, колебания агента, лишние прогоны."""
from __future__ import annotations

from ..render import bullets, fmt_dur, h1, h2, prev, table


def render(ctx, **opts) -> str:
    d = ctx.m
    top = int(opts.get("top", 12))
    out = [h1("Трение и лишние действия"), ""]
    out.append(bullets([
        "Два разных источника: что сказал пользователь и что думал агент. Не смешиваем.",
        "Слова ищутся в английском и русском вариантах.",
    ]))

    out.append(h2(f"Правки и указания пользователя ({len(d.user_hits)})"))
    out.append(table(
        ["обмен", "тип", "реплика"],
        [(h["exchange"], h["label"], h["preview"]) for h in d.user_hits[:top]],
        ["r", "l", "l"],
    ))

    out.append(h2(f"Колебания в рассуждении агента ({len(d.agent_hits)})"))
    out.append(table(
        ["обмен", "тип", "фрагмент"],
        [(h["exchange"], h["label"], h["preview"]) for h in d.agent_hits[:top]],
        ["r", "l", "l"],
    ))

    out.append(h2(f"Проверочные/симуляционные прогоны ({len(d.validation_runs)})"))
    out.append(table(
        ["обмен", "инструмент", "команда"],
        [(h["exchange"], h["name"], h["preview"]) for h in d.validation_runs[:top]],
        ["r", "l", "l"],
    ))

    gaps = sorted(d.gaps, key=lambda x: -x[1])[:6]
    out.append(h2("Долгие паузы перед запросом пользователя"))
    out.append("\n".join(f"- перед обменом {n}: {fmt_dur(g)}" for n, g in gaps) or "- нет")
    out.append("")
    return "\n".join(out)
