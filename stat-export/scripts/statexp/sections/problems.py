"""Срез: приоритетные аномалии с доказательствами."""
from __future__ import annotations

from ..model import burned, prev
from ..render import fmt_int, h1


def render(ctx, **opts) -> str:
    d = ctx.m
    items = []

    def add(sev, title, evidence, action):
        items.append(({"HIGH": 0, "MED": 1, "LOW": 2}[sev], sev, title, evidence, action))

    for e in d.err_finishes:
        add("HIGH", f"обмен {e['n']}: finish=error",
            f"ошибок инструментов: {sum(1 for t in e['tools'] if t['status'] == 'error')}; финалы: {e['finishes']}",
            f"`turn {e['n']}` — что сломалось и как агент вышел из ошибки")
    for n in sorted({t["exchange"] for t in d.err_tools}):
        group = [t for t in d.err_tools if t["exchange"] == n]
        sev = "HIGH" if len(group) >= 2 else "MED"
        add(sev, f"обмен {n}: {len(group)} ошибок инструментов",
            ", ".join(sorted({t["name"] for t in group})),
            f"`turn {n}`, затем `errors --only raw` — цепочка перепробованных вариантов")

    for key, group in sorted(d.dups.items(), key=lambda kv: -len(kv[1]))[:8]:
        add("HIGH" if len(group) >= 4 else "MED", f"повтор вызова `{key[0]}` ×{len(group)}",
            f"обмены {sorted({t['exchange'] for t in group})}; {prev(group[0]['input_preview'], 90)}",
            "`tools --only duplicates` — цикл или неверный запрос")
    for key, group in sorted(d.path_repeats.items(), key=lambda kv: -len(kv[1]))[:6]:
        add("MED", f"{key[1]} затронут {len(group)} раз через `{key[0]}`",
            f"обмены {sorted({t['exchange'] for t in group})}",
            "`tools` — перечитывание вместо правки")

    for r in d.reasons_by_size(3):
        if r["chars"] > 6000:
            add("MED", f"обмен {r['exchange']}: рассуждение {fmt_int(r['chars'])} симв.",
                prev(r["text"], 110), "`reasoning --top` и `turn` — долгое рассуждение перед решением")
    for t in d.big_inputs[:3]:
        if t["input_chars"] > 5000:
            add("MED", f"обмен {t['exchange']}: аргумент `{t['name']}` {fmt_int(t['input_chars'])} симв.",
                prev(t["input_preview"], 100), "`reasoning` — рассуждение в аргументе инструмента")
    for t in d.big_outputs[:3]:
        if t["out_chars"] > 20000:
            add("MED", f"обмен {t['exchange']}: вывод `{t['name']}` {fmt_int(t['out_chars'])} симв.",
                prev(t["out_text"], 100), "`tools --only size` — вывод съедает контекст")
    for ex in d.exs:
        if d.med_burn and burned(ex["tokens"]) > 2 * d.med_burn:
            add("MED", f"обмен {ex['n']}: выброс токенов "
                f"({fmt_int(burned(ex['tokens']))} против медианы {fmt_int(d.med_burn)})",
                f"in/out/r = {list(ex['tokens'].values())[:3]}", f"`turn {ex['n']}` — что именно съело токены")

    silent = [e["n"] for e in d.exs if e["reasoning"] and not e["texts"]]
    if silent:
        add("LOW", f"рассуждение без текста: {len(silent)} обменов", str(silent[:25]),
            "`reasoning` — модель молча думала перед инструментом")
    switched = [e["n"] for e in d.exs if any(v["type"] == "agent-switched" for v in e["events"])]
    if switched:
        add("LOW", f"смен агента: {len(switched)}", str(switched[:25]), "`timeline` — переключения режима")

    out = [h1("Проблемные зоны (по приоритету)"), ""]
    if not items:
        out.append("Явных аномалий не найдено.")
    for i, (_, sev, title, ev, act) in enumerate(sorted(items, key=lambda x: x[0]), 1):
        out += [f"{i}. **[{sev}] {title}**", f"   - факт: {ev}", f"   - проверить: {act}"]
    return "\n".join(out)
