"""Срез: аналитика вызовов инструментов."""
from __future__ import annotations

import statistics

from ..render import bullets, fmt_dur, fmt_int, h1, h2, prev, table


def render(ctx, **opts) -> str:
    d = ctx.m
    name = opts.get("name")
    only = opts.get("only")
    tools = [t for t in d.tools if not name or t["name"] == name]
    out = [h1("Инструменты"), ""]
    if name:
        out.append(bullets([f"Фильтр: `{name}`; вызовов: {len(tools)}"]))

    if only in (None, "summary"):
        out.append(h2("Сводка"))
        rows = []
        for nm in ([name] if name else [k for k, _ in d.by_name.most_common()]):
            st, ds = d.status_by_name[nm], d.dur_by_name[nm]
            rows.append((nm, sum(st.values()), st["completed"], st["error"],
                         int(statistics.mean(ds)) if ds else 0))
        out.append(table(["имя", "всего", "completed", "error", "средн. мс"], rows,
                         ["l", "r", "r", "r", "r"]))

    if only in (None, "errors"):
        errs = [t for t in tools if t["status"] == "error"]
        out.append(h2(f"Ошибки ({len(errs)})"))
        out.append("\n".join(
            f"- обмен {t['exchange']}, `{t['name']}` [{t.get('error_type', '-')}]: "
            f"{prev(t.get('error_text', '') or t['out_text'], 160)} ← {prev(t['input_preview'], 100)}"
            for t in errs[:40]
        ) or "- нет")
        if len(errs) > 40:
            out.append(f"- … и ещё {len(errs) - 40}")

    if only in (None, "duplicates"):
        dups = [(k, v) for k, v in d.dups.items() if not name or k[0] == name]
        out.append(h2(f"Повторы вызовов ({len(dups)} групп)"))
        out.append("\n".join(
            f"- `{k[0]}` ×{len(v)} в обменах {sorted({t['exchange'] for t in v})}: {prev(v[0]['input_preview'], 100)}"
            for k, v in sorted(dups, key=lambda kv: -len(kv[1]))[:25]
        ) or "- нет")
        reps = [(k, v) for k, v in d.path_repeats.items() if not name or k[0] == name]
        out.append(h2("Повторные пути (>=3)"))
        out.append("\n".join(
            f"- `{k[0]}` {k[1]} ×{len(v)} в обменах {sorted({t['exchange'] for t in v})}"
            for k, v in sorted(reps, key=lambda kv: -len(kv[1]))[:20]
        ) or "- нет")

    if only in (None, "size"):
        out.append(h2("Самые большие выводы"))
        out.append("\n".join(
            f"- обмен {t['exchange']}, `{t['name']}`: {fmt_int(t['out_chars'])} симв. — {prev(t['out_text'], 90)}"
            for t in d.big_outputs[:10] if not name or t["name"] == name
        ) or "- нет")
        out.append(h2("Самые большие аргументы"))
        out.append("\n".join(
            f"- обмен {t['exchange']}, `{t['name']}`: {fmt_int(t['input_chars'])} симв. — {prev(t['input_preview'], 90)}"
            for t in d.big_inputs[:10] if not name or t["name"] == name
        ) or "- нет")
        out.append(h2("Самые медленные вызовы"))
        out.append("\n".join(
            f"- обмен {t['exchange']}, `{t['name']}`: {fmt_dur(t['duration_ms'])} — {prev(t['input_preview'], 90)}"
            for t in d.slow_tools[:10] if not name or t["name"] == name
        ) or "- нет")
    out.append("")
    return "\n".join(out)
