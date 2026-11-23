"""Кэш и указатель: единственное место работы с файлами."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from . import sections
from .model import normalize

CACHE_ROOT = Path(tempfile.gettempdir()) / "stat-export"


class CacheStore:
    def __init__(self, session: Path, out: Path):
        self.session = session
        self.out = out

    def _key(self, sess: dict) -> str:
        raw = sess["meta"]["id"] + str(self.session.resolve())
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:90]

    def dir_for(self, sess: dict) -> Path:
        return CACHE_ROOT / self._key(sess)

    def from_export(self) -> dict:
        return normalize(json.loads(self.session.read_text(encoding="utf-8")))

    def build(self, sess: dict) -> Path:
        cdir = self.dir_for(sess)
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "cache.json").write_text(
            json.dumps(sess, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

        from .context import build as build_context  # отложенный импорт: build не требует аргументов CLI
        ctx = build_context(sess, None)
        for name in sections.FILE_SECTIONS:
            (cdir / f"{name}.md").write_text(sections.RENDERERS[name](ctx), encoding="utf-8")
        (cdir / "digest.md").write_text(sections.compose(ctx, self.digest_sections()), encoding="utf-8")

        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / f"{self.session.stem}.cache-path").write_text(str(cdir), encoding="utf-8")
        (self.out / f"{self.session.stem}.export.md").write_text(self._pointer(cdir, sess), encoding="utf-8")
        print(f"кэш: {cdir}")
        print(f"указатель: {self.out / (self.session.stem + '.export.md')}")
        return cdir

    def load(self) -> dict:
        pp = self.out / f"{self.session.stem}.cache-path"
        if not pp.exists():
            return self.build(self.from_export())
        cdir = Path(pp.read_text(encoding="utf-8").strip())
        if not (cdir / "cache.json").exists():
            return self.build(self.from_export())
        return json.loads((cdir / "cache.json").read_text(encoding="utf-8"))

    def clean(self) -> None:
        """Удалить всё временное для этой сессии; .tmp не трогается."""
        pp = self.out / f"{self.session.stem}.cache-path"
        cdir = None
        if pp.exists():
            try:
                cdir = Path(pp.read_text(encoding="utf-8").strip())
            except OSError:
                cdir = None
        if cdir is None and self.session.exists():
            try:
                cdir = self.dir_for(self.from_export())
            except (OSError, ValueError, KeyError):
                cdir = None

        removed = []
        if cdir is not None and cdir.parent == CACHE_ROOT and cdir.is_dir():
            shutil.rmtree(cdir)
            removed.append(str(cdir))
        for suffix in (".cache-path", ".export.md"):
            path = self.out / f"{self.session.stem}{suffix}"
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        if self.session.is_file() and self.session.parent == CACHE_ROOT:
            self.session.unlink()
            removed.append(str(self.session))
        print("удалено:" + ("\n  " + "\n  ".join(removed) if removed else " нечего"))

    @staticmethod
    def digest_sections() -> tuple[str, ...]:
        return ("overview", "index", "problems", "chains", "context",
                "skills", "friction", "enrichment")

    def _pointer(self, cdir: Path, sess: dict) -> str:
        exe = Path(__file__).resolve().parent.parent / "stat_export.py"
        s = self.session
        cmds = [
            f"python3 {exe} {s} build",
            f"python3 {exe} {s} digest",
            f"python3 {exe} {s} index",
            f"python3 {exe} {s} problems",
            f"python3 {exe} {s} chains --flagged",
            f"python3 {exe} {s} context",
            f"python3 {exe} {s} skills",
            f"python3 {exe} {s} friction",
            f"python3 {exe} {s} tools",
            f"python3 {exe} {s} reasoning",
            f"python3 {exe} {s} errors",
            f"python3 {exe} {s} timeline",
            f"python3 {exe} {s} turn 12",
            f"python3 {exe} {s} search 'phrase'",
            f"python3 {exe} {s} enrichment --db",
            f"python3 {exe} {s} clean",
        ]
        return "\n".join([
            "# stat-export — указатель", "",
            f"- сессия: `{s.resolve()}`",
            f"- заголовок: {sess['meta']['title']}; обменов: {len(sess['exchanges'])}",
            f"- кэш: `{cdir}`",
            f"- дайджест: `{cdir / 'digest.md'}`",
            "", "## Команды", "", "```sh", *cmds, "```", "",
            "Сырой экспорт целиком не читать — только срезы. БД подключается только `--db`.", "",
            "stat-export вызван напрямую — вписать `stat-export — прямой вызов` в Used STAT.md вручную.",
            "После stat-me выполнить `clean`: tmp удаляются, `.tmp` хранит только итоговый STAT.md.", "",
        ])
