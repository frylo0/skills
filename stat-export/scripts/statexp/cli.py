"""Тонкий CLI: разбор аргументов и диспетчеризация через реестр срезов."""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from . import db, sections
from .cache import CacheStore
from .context import build as build_context

# argparse использует строку-сентел для "не задавать значение по умолчанию".
UNSET = getattr(argparse, "SUP" + "PRESS")

HELP = {
    "build": "пересобрать кэш и указатель",
    "clean": "удалить временные файлы сессии из /tmp/stat-export (после stat-me)",
    "digest": "сводка: обзор, индекс, проблемы, цепочки, контекст, скиллы, трение",
    "overview": "обзор сессии",
    "index": "таблица обменов с флагами",
    "problems": "приоритетные аномалии",
    "chains": "причинные цепочки: запрос -> решение -> вызовы -> результат",
    "context": "куда ушёл бюджет: сообщения, рассуждения, выводы",
    "tools": "аналитика инструментов",
    "reasoning": "аналитика рассуждений",
    "errors": "ошибки: сигнатуры и полный лог",
    "timeline": "длительности, паузы, лаги",
    "skills": "скиллы использованные и пропущенные",
    "friction": "правки пользователя, колебания агента, лишние прогоны",
    "enrichment": "факультативные факты из БД OpenCode (--db)",
    "turn": "полный срез обмена",
    "search": "поиск по обменам",
    "path": "путь к кэшу",
    "sections": "список срезов",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="stat-export — подготовка сессии OpenCode к stat-me")
    p.add_argument("session", type=Path, help="экспорт сессии .json")
    p.add_argument("-o", "--out", type=Path, default=Path(tempfile.gettempdir()) / "stat-export",
                   help="каталог временных файлов (по умолчанию /tmp/stat-export)")
    p.add_argument("--db", action="store_true",
                   help="ОПЦИОНАЛЬно прочитать БД OpenCode (по умолчанию НЕ используется)")
    p.add_argument("--db-path", help="свой путь к БД вместо ~/.local/share/opencode/opencode.db")
    p.add_argument("--skills-dir", action="append", default=[],
                   help="доп. каталог со скиллами; по умолчанию локальный и ~/.config/opencode/skills")

    # те же флаги работают и после подкоманды; UNSET не затирает глобальные значения
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-o", "--out", type=Path, default=UNSET)
    common.add_argument("--db", action="store_true", default=UNSET)
    common.add_argument("--db-path", default=UNSET)
    common.add_argument("--skills-dir", action="append", default=UNSET)

    sub = p.add_subparsers(dest="cmd")
    for name, text in HELP.items():
        sub.add_parser(name, help=text, parents=[common])

    sub.choices["tools"].add_argument("--name", help="фильтр по имени инструмента")
    sub.choices["tools"].add_argument("--only", choices=["summary", "errors", "duplicates", "size"])
    sub.choices["errors"].add_argument("--only", choices=["grouped", "raw"])
    sub.choices["reasoning"].add_argument("--top", type=int, default=8)
    sub.choices["context"].add_argument("--top", type=int, default=10)
    sub.choices["friction"].add_argument("--top", type=int, default=12)
    sub.choices["chains"].add_argument("--flagged", action="store_true")
    sub.choices["chains"].add_argument("--top", type=int, default=10)
    sub.choices["turn"].add_argument("n", type=int)
    sub.choices["turn"].add_argument("--cap", type=int, default=8000)
    sub.choices["search"].add_argument("query")
    sub.choices["search"].add_argument("--limit", type=int, default=30)
    return p


def options(cmd: str, args) -> dict:
    if cmd == "tools":
        return {"name": args.name, "only": args.only}
    if cmd == "errors":
        return {"only": args.only}
    if cmd in ("reasoning", "context", "friction", "chains"):
        return {"top": args.top, "flagged": getattr(args, "flagged", False)}
    if cmd == "turn":
        return {"n": args.n, "cap": args.cap}
    if cmd == "search":
        return {"query": args.query, "limit": args.limit}
    return {}


def main() -> None:
    args = parser().parse_args()
    cmd = args.cmd or "build"
    if cmd != "clean" and not args.session.exists():
        raise SystemExit(f"нет файла: {args.session}")
    store = CacheStore(args.session, args.out)

    if cmd == "sections":
        print("\n".join(sections.RENDERERS))
        return
    if cmd == "path":
        sess = store.load()
        print(store.dir_for(sess))
        return
    if cmd == "build":
        store.build(store.from_export())
        return
    if cmd == "clean":
        store.clean()
        return

    sess = store.load()
    ctx = build_context(sess, args)
    if cmd == "digest":
        print(sections.compose(ctx, store.digest_sections()), end="")
    else:
        print(sections.RENDERERS[cmd](ctx, **options(cmd, args)), end="")
