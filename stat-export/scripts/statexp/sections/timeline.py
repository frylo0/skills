"""Срез: хронология, паузы и лаги инструментов."""
from __future__ import annotations

from ..model import burned
from ..render import fmt_clock, fmt_dur, fmt_int, h1, h2, table


def render(ctx, **opts) -> str:
    d, tm = ctx.m, ctx.meta["time"]
    out = [h1("Хронология"), ""]
    out.append(h2("Обмены по длительности"))
    out.append(table(
        ["#", "dur", "токены", "флаги"],
        [(e["n"], fmt_dur(e["duration_ms"]), fmt_int(burned(e["tokens"])),
          ",".join(d.flags.get(e["n"], [])) or "-")
         for e in sorted(d.exs, key=lambda e: -e["duration_ms"])[:10]],
        ["r", "l", "r", "l"],
    ))
    gaps = [(n, g) for n, g in d.gaps if g > 30000]
    out.append(h2("Паузы между обменами (>30с)"))
    out.append("\n".join(f"- перед обменом {n}: {fmt_dur(g)}"
                         for n, g in sorted(gaps, key=lambda x: -x[1])[:12]) or "- нет")
    out.append(h2("Самые медленные инструменты"))
    out.append(table(
        ["обмен", "инструмент", "dur"],
        [(t["exchange"], t["name"], fmt_dur(t["duration_ms"])) for t in d.slow_tools[:10]],
        ["r", "l", "l"],
    ))
    out.append("")
    return "\n".join(out)
