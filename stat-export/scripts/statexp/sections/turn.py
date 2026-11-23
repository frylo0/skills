"""Срез: один обмен целиком."""
from __future__ import annotations

from ..model import prev
from ..render import bullets, fmt_clock, fmt_dur, fmt_int, h1, h2, table


def render(ctx, **opts) -> str:
    n = int(opts.get("n", 1))
    cap = int(opts.get("cap", 8000))
    exs = ctx.m.exs
    if n < 1 or n > len(exs):
        raise SystemExit(f"нет обмена {n}; всего {len(exs)}")
    ex = exs[n - 1]
    tk = ex["tokens"]
    out = [h1(f"Обмен {n}"), ""]
    out.append(bullets([
        f"время: {fmt_clock(ex['started'])} UTC; длительность: {fmt_dur(ex['duration_ms'])}; "
        f"стоимость: ${ex['cost']:.4f}; finish: {ex['finishes']}",
        f"токены: in {fmt_int(tk['input'])}, out {fmt_int(tk['output'])}, "
        f"reasoning {fmt_int(tk['reasoning'])}, cache read {fmt_int(tk['cache_read'])}",
        f"флаги: {','.join(ctx.m.flags.get(n, [])) or '-'}",
    ]))
    out.append(h2("Запрос пользователя"))
    for u in ex["user"]:
        out.append(u["text"] or "(пусто)")
        if u["skills"]:
            out.append(f"скиллы: {', '.join(str(s.get('id') or s.get('name') or s) if isinstance(s, dict) else str(s) for s in u['skills'])}")
    out.append(h2("Рассуждение"))
    for r in ex["reasoning"]:
        txt = r["text"]
        out.append(txt[:cap] + ("\n\n… (обрезано)" if len(txt) > cap else "") + "\n\n---")
    out.append(h2("Ответ"))
    for t in ex["texts"]:
        out.append(t["text"][:cap] + ("\n\n… (обрезано)" if len(t["text"]) > cap else ""))
    out.append(h2("Инструменты"))
    out.append(table(
        ["имя", "статус", "dur", "input", "вывод (симв.)"],
        [(t["name"], t["status"], fmt_dur(t["duration_ms"]),
          prev(t["input_preview"], 70), fmt_int(t["out_chars"])) for t in ex["tools"]],
        ["l", "l", "l", "l", "r"],
    ))
    errs = [t for t in ex["tools"] if t["status"] == "error"]
    if errs:
        out.append(h2("Сообщения об ошибках"))
        out += [f"- `{t['name']}` [{t.get('error_type', '-')}]: "
                f"{prev(t.get('error_text', '') or t['out_text'], 400)}" for t in errs]
    out.append("")
    return "\n".join(out)
