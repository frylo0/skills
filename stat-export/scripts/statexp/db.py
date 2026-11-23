"""ОПЦИОНАЛЬное обогащение из БД OpenCode.

По умолчанию НЕ используется: JSON-экспорт покрывает >90% данных.
БД подключается только явным `--db PATH` / `--db` (путь по умолчанию).
Читаем только сессионные таблицы, никогда — account/credential/blob.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB = "~/.local/share/opencode/opencode.db"


def _count(c, table: str, col: str, sid: str) -> int:
    try:
        return c.execute(f"SELECT count(*) FROM {table} WHERE {col}=?", (sid,)).fetchone()[0]
    except sqlite3.Error:
        return -1


def _groups(c, query: str, sid: str) -> dict:
    try:
        return {str(k): v for k, v in c.execute(query, (sid,))}
    except sqlite3.Error:
        return {}


def load(session_id: str, path: str | None = None) -> dict:
    p = Path(path or DEFAULT_DB).expanduser()
    facts = {"enabled": True, "path": str(p), "available": False, "reason": "", "facts": {},
             "children": [], "counts": {}}
    if not p.exists():
        facts["reason"] = "файл БД не найден"
        return facts
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=2)
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM session_v2 WHERE id=?", (session_id,)).fetchone()
        if row is None:
            facts["reason"] = "сессия в БД не найдена"
            c.close()
            return facts
        keys = ("slug", "version", "parent_id", "fork_session_id", "time_compacting",
                "time_archived", "time_suspended", "resume_attempts", "idle_outcome",
                "summary_files", "summary_additions", "summary_deletions", "metadata")
        facts["facts"] = {k: row[k] for k in keys if k in row.keys()}
        facts["available"] = True
        facts["counts"] = {
            "session_message": _count(c, "session_message", "session_id", session_id),
            "event": _count(c, "event", "aggregate_id", session_id),
            "todo": _count(c, "todo", "session_id", session_id),
            "job": _count(c, "job", "session_id", session_id),
            "session_inbox": _count(c, "session_inbox", "session_id", session_id),
            "events_by_type": _groups(c, "SELECT type, count(*) FROM event WHERE aggregate_id=? GROUP BY type", session_id),
            "todos_by_status": _groups(c, "SELECT status, count(*) FROM todo WHERE session_id=? GROUP BY status", session_id),
        }
        for r in c.execute(
            "SELECT id, title, cost, tokens_input, tokens_output, tokens_reasoning "
            "FROM session_v2 WHERE parent_id=? OR fork_session_id=?", (session_id, session_id)
        ):
            facts["children"].append(dict(r))
        c.close()
    except Exception as e:  # нет доступа, занята БД, другая версия схемы — не ломаем разбор
        facts["reason"] = f"{type(e).__name__}: {e}"
    return facts


def disabled() -> dict:
    return {"enabled": False, "available": False, "reason": "БД не подключена — экспорт является источником данных",
            "facts": {}, "children": [], "counts": {}}
