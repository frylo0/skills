"""Реестр срезов. Новый срез = новый модуль + одна строка здесь."""
from __future__ import annotations

from . import (chains, context_view, enrichment, errors, friction, index, overview,
               problems, reasoning, skills_ledger, timeline, tools, turn, search)

RENDERERS = {
    "overview": overview.render,
    "index": index.render,
    "problems": problems.render,
    "chains": chains.render,
    "context": context_view.render,
    "tools": tools.render,
    "reasoning": reasoning.render,
    "errors": errors.render,
    "timeline": timeline.render,
    "skills": skills_ledger.render,
    "friction": friction.render,
    "enrichment": enrichment.render,
    "turn": turn.render,
    "search": search.render,
}

# файлы, которые пишет build (интерактивные turn/search исключены)
FILE_SECTIONS = tuple(k for k in RENDERERS if k not in ("turn", "search"))


def compose(ctx, names, **opts) -> str:
    return "\n".join(RENDERERS[name](ctx, **opts) for name in names)
