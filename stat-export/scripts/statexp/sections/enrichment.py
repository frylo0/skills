"""Срез: факультативные факты из БД OpenCode (только по --db)."""
from __future__ import annotations

from ..render import bullets, h1, h2, table


def render(ctx, **opts) -> str:
    e = ctx.db
    out = [h1("Обогащение из БД"), ""]
    if not e["enabled"]:
        out.append(bullets([
            e["reason"] + ".",
            "Чтобы подключить: `... <session.json> enrichment --db` (или `--db PATH`).",
        ]))
        return "\n".join(out)
    if not e["available"]:
        out.append(bullets([f"БД недоступна: {e['reason']}.", f"Путь: `{e['path']}`."]))
        return "\n".join(out)

    out.append(bullets([f"БД: `{e['path']}`; сессия найдена."]))
    out.append(h2("Поля сессии"))
    out.append(table(
        ["поле", "значение"],
        [(k, str(v)[:120] if v is not None else "-") for k, v in e["facts"].items()],
        ["l", "l"],
    ))
    out.append(h2("Связанные сессии (children/forks)"))
    out.append(table(
        ["id", "заголовок", "cost", "in/out/r"],
        [(c["id"], c["title"], c["cost"],
          f"{c['tokens_input']}/{c['tokens_output']}/{c['tokens_reasoning']}") for c in e["children"]],
        ["l", "l", "r", "l"],
    ) if e["children"] else "- нет")
    out.append(h2("Счётчики"))
    out.append("\n".join(f"- {k}: {v}" for k, v in e["counts"].items()))
    out.append("")
    return "\n".join(out)
