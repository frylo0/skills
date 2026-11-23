"""Срез: ошибки — группировка по сигнатурам и полный лог."""
from __future__ import annotations

from ..render import bullets, h1, h2, prev, table


def render(ctx, **opts) -> str:
    d = ctx.m
    only = opts.get("only")
    out = [h1("Ошибки"), ""]
    out.append(bullets([
        f"ошибок инструментов: {len(d.err_tools)}; обменов с finish=error: {len(d.err_finishes)}",
    ]))
    if only in (None, "grouped"):
        out.append(h2("Сигнатуры (одинаковые ошибки свернуты)"))
        out.append(table(
            ["кол-во", "инструмент", "обмены", "сигнатура", "пример входа"],
            [(len(g["items"]), g["name"], str(g["exchanges"])[:40],
              f"{g['items'][0].get('error_type', '-')}: {prev(g['signature'], 100)}",
              prev(g["items"][0]["input_preview"], 90)) for g in d.error_groups[:30]],
            ["r", "l", "l", "l", "l"],
        ))
    if only in (None, "raw"):
        out.append(h2("Полный лог"))
        out.append(table(
            ["обмен", "инструмент", "тип ошибки", "сообщение", "input"],
            [(t["exchange"], t["name"], t.get("error_type", "-"),
              prev(t.get("error_text", "") or t["out_text"], 120),
              prev(t["input_preview"], 80)) for t in d.err_tools],
            ["r", "l", "l", "l", "l"],
        ))
    if d.err_finishes:
        out.append(h2("Обмены с finish=error"))
        out.append("\n".join(
            f"- обмен {e['n']}: {e['finishes']}; инструментов {len(e['tools'])}; "
            f"последний текст: {prev(e['texts'][-1]['text'], 120) if e['texts'] else '-'}"
            for e in d.err_finishes
        ))
    out.append("")
    return "\n".join(out)
