"""Учёт скиллов: что реально вызвали и чего, судя по описаниям, не хватило.

Эвристика «skipped» — кандидаты по совпадению слов, а не доказанный факт.
"""
from __future__ import annotations

import collections
import re
from pathlib import Path

from .model import prev, user_text

# локальный и глобальный OpenCode + дефолты skills.sh (.agents/skills в проекте и в ~)
DEFAULT_DIRS = (".opencode/skills", "~/.config/opencode/skills",
                ".agents/skills", "~/.agents/skills")
STOP = {
    "that", "this", "with", "from", "when", "what", "which", "your", "have", "into", "need",
    "when", "used", "work", "skill", "skills", "when", "with", "чтобы", "котор", "которая",
    "которые", "если", "это", "для", "как", "что", "или", "при", "или", "более", "менее",
    "скилл", "скиллы", "задача", "задачи", "работа", "помощь", "нужно", "можно", "только",
}
USE_WHEN = re.compile(r"USE WHEN:\s*(.*?)(?:\n\s*NOT FOR:|$)", re.I | re.S)


def configured_dirs(extra=()) -> list[Path]:
    dirs = []
    for raw in (*DEFAULT_DIRS, *extra):
        p = Path(raw).expanduser()
        if p not in dirs:
            dirs.append(p)
    return dirs


def skill_dirs(extra=()) -> list[Path]:
    return [d for d in configured_dirs(extra) if d.is_dir()]


def parse_description(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            parts = [line.split(":", 1)[1].strip()]
            j = i + 1
            while j < len(lines) and lines[j].strip() != "---" and not re.match(r"^[A-Za-z_-]+:", lines[j]):
                parts.append(lines[j].strip())
                j += 1
            return re.sub(r"^[>+|-]+\s*", "", " ".join(parts))
    return ""


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Zа-яА-ЯёЁ]{4,}", text.lower()) if w not in STOP}


def skill_name(v) -> str:
    if isinstance(v, dict):
        return str(v.get("id") or v.get("name") or "")
    return str(v or "")


def collect(sess: dict, extra_dirs=()) -> dict:
    used = []
    # stat-export вызван напрямую, чтобы подготовить этот разбор; в экспорте сессии
    # такой вызов не reflected, поэтому добавляем фактом, а не из данных.
    used.append({"name": "stat-export", "exchange": "—",
                 "source": "прямой вызов (подготовка сессии к разбору)"})
    for ex in sess["exchanges"]:
        text = user_text(ex)
        for s in (ex["user"][0].get("skills") if ex["user"] else []) or []:
            name = skill_name(s)
            if not name:
                continue
            used.append({"name": name, "exchange": ex["n"],
                         "source": "явный @скилл" if f"@{name.lower()}" in text.lower() else "по описанию/tools"})
        for t in ex["tools"]:
            if t["name"] == "skill":
                name = skill_name(t["input"])
                if name and not any(u["name"] == name and u["exchange"] == ex["n"] for u in used):
                    used.append({"name": name, "exchange": ex["n"], "source": "вызов инструмента skill"})

    used_names = {u["name"] for u in used}
    user_corpus = " ".join(user_text(ex) for ex in sess["exchanges"])
    corpus_words = words(user_corpus)
    doc_freq = collections.Counter()
    for ex in sess["exchanges"]:
        doc_freq.update(words(user_text(ex)))
    # слова, встречающиеся почти в каждом обмене, не говорят о конкретном скилле
    max_df = max(2, int(0.15 * max(1, len(sess["exchanges"]))))
    distinctive = {w for w in corpus_words if doc_freq[w] <= max_df}

    candidates = []
    dirs = skill_dirs(extra_dirs)
    for d in dirs:
        for path in sorted(d.glob("*/SKILL.md")):
            name = path.parent.name
            if name in used_names:
                continue
            desc = parse_description(path)
            trigger = USE_WHEN.search(desc)
            trig_words = words(trigger.group(1)) if trigger else set()
            all_words = words(desc)
            matched = sorted((trig_words | all_words) & distinctive)
            score = len(set(matched) & trig_words) * 3 + len(matched)
            # слова должны встретиться вместе хотя бы в двух обменах — иначе совпадение случайное
            coincidences = [
                ex["n"] for ex in sess["exchanges"]
                if len(words(user_text(ex)) & trig_words & distinctive) >= 2
            ]
            if score >= 3 and len(coincidences) >= 2:
                candidates.append({"name": name, "score": score,
                                   "matched": matched[:12], "exchanges": coincidences[:6],
                                   "trigger": prev(trigger.group(1), 160) if trigger else ""})
    candidates.sort(key=lambda c: -c["score"])
    unique = {}
    for c in candidates:  # один и тот же каталог может быть смонтирован дважды
        unique.setdefault(c["name"], c)
    candidates = list(unique.values())

    return {
        "used": used,
        "skipped": candidates[:6],
        "dirs": [str(d) for d in dirs],
        "all_dirs": [(str(d), d in dirs) for d in configured_dirs(extra_dirs)],
        "note": "skipped — эвристика по совпадению слов в USE WHEN и текстах запросов, не факт.",
    }
