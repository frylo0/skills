"""Нормализация экспорта OpenCode и общие доступы к данным.

Здесь только структура и элементарные утилиты: никакой аналитики и форматирования.
"""
from __future__ import annotations

import hashlib
import json


def clean(s) -> str:
    return " ".join(str(s if s is not None else "").split())


def prev(s, n: int = 150) -> str:
    s = clean(s)
    return s[:n] + ("…" if len(s) > n else "")


def jdump(o, limit: int | None = None) -> str:
    s = json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return s[:limit] + "…" if limit and len(s) > limit else s


def digest(o) -> str:
    return hashlib.sha256(jdump(o).encode("utf-8")).hexdigest()[:12]


def num(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def ms(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def span(a, b) -> int:
    a, b = ms(a), ms(b)
    return max(0, b - a) if a is not None and b is not None else 0


def zero_tokens() -> dict:
    return {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}


def parse_tokens(t) -> dict:
    t = t or {}
    c = t.get("cache") or {}
    return {
        "input": int(num(t.get("input"))),
        "output": int(num(t.get("output"))),
        "reasoning": int(num(t.get("reasoning"))),
        "cache_read": int(num(c.get("read"))),
        "cache_write": int(num(c.get("write"))),
    }


def add_tokens(a: dict, b: dict) -> dict:
    return {k: a[k] + b[k] for k in a}


def burned(t: dict) -> int:
    """Токены без cache read — реально потраченный бюджет."""
    return t["input"] + t["output"] + t["reasoning"]


def path_of(inp: dict):
    for key in ("path", "file_path", "file", "filename"):
        v = inp.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def normalize(raw: dict) -> dict:
    """Привести info+messages к списку обменов (запрос -> ассистент -> инструменты)."""
    info = raw.get("info") or {}
    exchanges: list[dict] = []
    cur: dict | None = None

    def new_exchange() -> dict:
        return {
            "n": len(exchanges) + 1,
            "started": None,
            "ended": None,
            "duration_ms": 0,
            "user": [],
            "events": [],
            "assistant": [],
            "tools": [],
            "reasoning": [],
            "texts": [],
            "tokens": zero_tokens(),
            "cost": 0.0,
            "finishes": [],
        }

    for m in raw.get("messages") or []:
        typ = m.get("type")
        tm = m.get("time") or {}
        created = ms(tm.get("created"))

        if typ == "user":
            cur = new_exchange()
            cur["started"] = created
            cur["user"].append({
                "text": m.get("text") or "",
                "files": m.get("files") or [],
                "skills": m.get("skills") or [],
                "time": created,
            })
            exchanges.append(cur)
            continue

        if cur is None:
            cur = new_exchange()
            cur["started"] = created
            exchanges.append(cur)

        cur["events"].append({
            "type": typ,
            "agent": m.get("agent"),
            "previous": m.get("previous"),
            "outcome": m.get("outcome"),
            "time": created,
        })

        if typ == "assistant":
            am = {
                "id": m.get("id"),
                "agent": m.get("agent"),
                "finish": m.get("finish"),
                "time": tm,
                "tokens": parse_tokens(m.get("tokens")),
                "cost": num(m.get("cost")),
                "reasoning": [],
                "texts": [],
                "tools": [],
            }
            for p in m.get("content") or []:
                pt = p.get("type")
                if pt == "reasoning":
                    text = p.get("text") or ""
                    item = {"text": text, "chars": len(text), "native": p.get("native"),
                            "time": p.get("time") or {}}
                    am["reasoning"].append(item)
                    cur["reasoning"].append(dict(item, exchange=cur["n"], msg=m.get("id")))
                elif pt == "text":
                    text = p.get("text") or ""
                    item = {"text": text, "chars": len(text)}
                    am["texts"].append(item)
                    cur["texts"].append(dict(item, exchange=cur["n"]))
                elif pt == "tool":
                    st = p.get("state") or {}
                    inp = st.get("input") or {}
                    err = st.get("error") or {}
                    if not isinstance(err, dict):
                        err = {"message": str(err)}
                    out = "\n".join(
                        c.get("text", "") for c in (st.get("content") or [])
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
                    tt = p.get("time") or {}
                    tool = {
                        "id": p.get("id"),
                        "name": p.get("name") or "?",
                        "status": st.get("status") or "?",
                        "error_type": err.get("type") or "-",
                        "error_text": str(err.get("message") or ""),
                        "input": inp,
                        "input_chars": len(jdump(inp)),
                        "input_hash": digest(inp),
                        "input_preview": prev(jdump(inp), 180),
                        "out_chars": len(out),
                        "out_text": out,
                        "metadata": st.get("metadata") or {},
                        "created": ms(tt.get("created")),
                        "ran": ms(tt.get("ran")),
                        "completed": ms(tt.get("completed")),
                        "duration_ms": span(tt.get("created"), tt.get("completed")),
                        "path": path_of(inp),
                        "exchange": cur["n"],
                        "msg": m.get("id"),
                    }
                    am["tools"].append(tool)
                    cur["tools"].append(tool)
            cur["assistant"].append(am)
            cur["tokens"] = add_tokens(cur["tokens"], am["tokens"])
            cur["cost"] += am["cost"]
            if m.get("finish"):
                cur["finishes"].append(m.get("finish"))
            cur["ended"] = ms(tm.get("completed")) or created
        else:
            cur["ended"] = created

    for ex in exchanges:
        ex["duration_ms"] = span(ex["started"], ex["ended"])

    model = info.get("model") or {}
    return {
        "meta": {
            "id": info.get("id") or digest(str(raw.get("messages"))[:1000]),
            "title": info.get("title") or "(без заголовка)",
            "project": ((info.get("location") or {}).get("directory") or "-"),
            "agent": info.get("agent") or "-",
            "model": model.get("id") or "-",
            "variant": model.get("variant") or "-",
            "outcome": info.get("outcome") or "-",
            "cost": num(info.get("cost")),
            "tokens": parse_tokens(info.get("tokens")),
            "time": info.get("time") or {},
            "message_count": len(raw.get("messages") or []),
        },
        "exchanges": exchanges,
    }


def iter_tools(sess: dict):
    for ex in sess["exchanges"]:
        yield from ex["tools"]


def iter_reasons(sess: dict):
    for ex in sess["exchanges"]:
        yield from ex["reasoning"]


def iter_texts(sess: dict):
    for ex in sess["exchanges"]:
        yield from ex["texts"]


def iter_assistant(sess: dict):
    for ex in sess["exchanges"]:
        for am in ex["assistant"]:
            yield ex["n"], am


def user_text(ex: dict) -> str:
    return " ".join(u.get("text") or "" for u in ex.get("user") or [])
