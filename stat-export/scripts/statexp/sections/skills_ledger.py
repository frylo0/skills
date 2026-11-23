"""Срез: скиллы использованные и кандидаты на пропуск."""
from __future__ import annotations

from ..render import bullets, h1, h2, prev, table


def render(ctx, **opts) -> str:
    s = ctx.skills
    out = [h1("Скиллы"), ""]
    out.append(h2(f"Использованы ({len(s['used'])})"))
    out.append(table(
        ["скилл", "обмен", "как вызван"],
        [(u["name"], u["exchange"], u["source"]) for u in s["used"]],
        ["l", "r", "l"],
    ))
    out.append(h2(f"Кандидаты на пропуск ({len(s['skipped'])})"))
    out.append(table(
        ["скилл", "score", "обмены", "совпавшие слова", "USE WHEN"],
        [(c["name"], c["score"], str(c.get("exchanges", [])[:6]),
          ", ".join(c["matched"][:8]), prev(c["trigger"], 110))
         for c in s["skipped"]],
        ["l", "r", "l", "l", "l"],
    ))
    catalogs = ", ".join(f"`{p}`" + ("" if ok else " (нет)")
                         for p, ok in s.get("all_dirs") or [(d, True) for d in s["dirs"]])
    out.append(bullets([s["note"], "Каталоги: " + catalogs + "."]))
    out.append("")
    return "\n".join(out)
