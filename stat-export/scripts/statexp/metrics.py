"""Все производные факты и флаги сессии. Одно место на всю аналитику.

Секции не считают ничего сами — они только читают Metrics.
"""
from __future__ import annotations

import collections
import re
import statistics

from .model import burned, clean, iter_assistant, iter_reasons, iter_texts, iter_tools, jdump, prev

FLAG_HELP = {
    "ERR": "ошибка инструмента или finish=error",
    "DUP": "одинаковый вызов инструмента",
    "REPEAT": "один путь >=3 раз",
    "SILENT": "рассуждение без ответа пользователю",
    "HI-TOK": "сожжено токенов вдвое больше медианы",
    "SLOW": "длительность вдвое больше медианы",
    "SWITCH": "смена агента внутри обмена",
    "BIG-IN": "аргумент инструмента >5000 симв.",
    "BIG-OUT": "вывод инструмента >20000 симв.",
}

USER_CORRECTIONS = [
    ("отрицание", r"\b(no|not this|wrong|stop|revert|instead|rather|actually|i meant|don'?t|не надо|не так|нет|вместо|неправильно|стоп|откати|я имел|хватит)\b"),
    ("вопрос-почему", r"\b(why|почему|зачем)\b"),
    ("уточнение", r"\b(i said|just create|only files|только файлы|я сказал|просто создай)\b"),
]
AGENT_HESITATION = [
    ("неуверенность", r"\b(hmm|not sure|should i|let me decide|let'?s decide|хм|не уверен|надо решить|давай решим)\b"),
    ("пересмотр", r"\b(wait|alternative|подожди|альтернативно|вместо этого)\b"),
]
VALIDATION_RUN = re.compile(
    r"(simulat|render[-_ ]?test|\btest\b|py_compile|make -n|dry.?run|"
    r"тест|симуляц|проверк|рендер[-_ ]?тест)", re.I)


class Metrics:
    def __init__(self, sess: dict):
        self.sess = sess
        self.exs = sess["exchanges"]
        self.tools = list(iter_tools(sess))
        self.reasons = list(iter_reasons(sess))
        self.texts = list(iter_texts(sess))
        self._tool_stats()
        self._errors()
        self._duplicates()
        self._hotspots()
        self._friction()
        self._flags()
        self._gaps()

    # --- инструменты ---
    def _tool_stats(self):
        self.by_name = collections.Counter(t["name"] for t in self.tools)
        self.by_status = collections.Counter(t["status"] for t in self.tools)
        self.status_by_name = collections.defaultdict(collections.Counter)
        self.dur_by_name = collections.defaultdict(list)
        for t in self.tools:
            self.status_by_name[t["name"]][t["status"]] += 1
            self.dur_by_name[t["name"]].append(t["duration_ms"])
        self.big_outputs = sorted(self.tools, key=lambda t: t["out_chars"], reverse=True)[:8]
        self.big_inputs = sorted(self.tools, key=lambda t: t["input_chars"], reverse=True)[:8]
        self.slow_tools = sorted(self.tools, key=lambda t: t["duration_ms"], reverse=True)[:8]

    def _duplicates(self):
        groups = collections.defaultdict(list)
        for t in self.tools:
            groups[(t["name"], t["input_hash"])].append(t)
        self.dups = {k: v for k, v in groups.items() if len(v) > 1}
        self.dup_exchanges = {t["exchange"] for v in self.dups.values() for t in v}

        paths = collections.defaultdict(list)
        for t in self.tools:
            if t["path"]:
                paths[(t["name"], t["path"])].append(t)
        self.path_repeats = {k: v for k, v in paths.items() if len(v) >= 3}
        self.repeat_exchanges = {t["exchange"] for v in self.path_repeats.values() for t in v}

    # --- ошибки ---
    def _errors(self):
        self.err_tools = [t for t in self.tools if t["status"] == "error"]
        self.err_finishes = [e for e in self.exs if "error" in e["finishes"]]
        groups = collections.defaultdict(list)
        for t in self.err_tools:
            sig = clean(t.get("error_text", ""))[:130] or clean(t["out_text"])[:130] or clean(t["input_preview"])[:130] or "(пусто)"
            groups[(t["name"], sig)].append(t)
        self.error_groups = [
            {"name": k[0], "signature": k[1], "items": v,
             "exchanges": sorted({t["exchange"] for t in v})}
            for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))
        ]

    # --- токены ---
    def _hotspots(self):
        self.hotspots = []
        for n, am in iter_assistant(self.sess):
            body = am["texts"][0]["text"] if am["texts"] else (
                am["reasoning"][0]["text"] if am["reasoning"] else "")
            self.hotspots.append({
                "exchange": n, "msg": am["id"], "agent": am["agent"],
                "tokens": burned(am["tokens"]), "detail": am["tokens"],
                "tools": len(am["tools"]), "finish": am["finish"], "preview": prev(body, 110),
            })
        self.hotspots.sort(key=lambda h: -h["tokens"])
        burns = [burned(e["tokens"]) for e in self.exs]
        self.med_burn = statistics.median(burns) if burns else 0
        self.max_burn = max(burns) if burns else 0

    # --- трение ---
    def _friction(self):
        self.user_hits = []
        self.agent_hits = []
        self.validation_runs = []
        for ex in self.exs:
            u_text = " ".join(u.get("text") or "" for u in ex["user"])
            for label, pattern in USER_CORRECTIONS:
                if re.search(pattern, u_text, re.I):
                    self.user_hits.append({"exchange": ex["n"], "label": label,
                                           "preview": prev(u_text, 160)})
            for r in ex["reasoning"]:
                for label, pattern in AGENT_HESITATION:
                    if re.search(pattern, r["text"], re.I):
                        self.agent_hits.append({"exchange": ex["n"], "label": label,
                                                "preview": prev(r["text"], 160)})
                        break
            for t in ex["tools"]:
                if t["name"] in ("shell", "execute") and VALIDATION_RUN.search(jdump(t["input"])):
                    self.validation_runs.append({"exchange": ex["n"], "name": t["name"],
                                                 "preview": prev(t["input_preview"], 140)})

    # --- флаги ---
    def _flags(self):
        self.flags: dict[int, list[str]] = collections.defaultdict(list)
        durations = [e["duration_ms"] for e in self.exs]
        self.med_dur = statistics.median(durations) if durations else 0
        self.max_dur = max(durations) if durations else 0
        for e in self.exs:
            n = e["n"]
            if any(t["status"] == "error" for t in e["tools"]) or "error" in e["finishes"]:
                self.flags[n].append("ERR")
            if n in self.dup_exchanges:
                self.flags[n].append("DUP")
            if n in self.repeat_exchanges:
                self.flags[n].append("REPEAT")
            if e["reasoning"] and not e["texts"]:
                self.flags[n].append("SILENT")
            if self.med_burn and burned(e["tokens"]) > 2 * self.med_burn:
                self.flags[n].append("HI-TOK")
            if self.med_dur and e["duration_ms"] > 2 * self.med_dur:
                self.flags[n].append("SLOW")
            if any(v["type"] == "agent-switched" for v in e["events"]):
                self.flags[n].append("SWITCH")
            if any(t["out_chars"] > 20000 for t in e["tools"]):
                self.flags[n].append("BIG-OUT")
            if any(t["input_chars"] > 5000 for t in e["tools"]):
                self.flags[n].append("BIG-IN")

    def _gaps(self):
        self.gaps = []
        for a, b in zip(self.exs, self.exs[1:]):
            if a["ended"] and b["started"]:
                self.gaps.append((b["n"], max(0, b["started"] - a["ended"])))

    # --- общее ---
    def flagged(self) -> list[dict]:
        return [e for e in self.exs if self.flags.get(e["n"])]

    def reasons_by_size(self, top: int = 8):
        return sorted(self.reasons, key=lambda r: -r["chars"])[:top]
