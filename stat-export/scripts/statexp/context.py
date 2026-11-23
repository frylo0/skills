"""Контекст рендерера: один объект на все срезы."""
from __future__ import annotations

from dataclasses import dataclass

from . import db, skills
from .metrics import Metrics


@dataclass
class Ctx:
    sess: dict
    m: Metrics
    skills: dict
    db: dict
    args: object | None = None

    @property
    def meta(self) -> dict:
        return self.sess["meta"]


def build(sess: dict, args=None) -> Ctx:
    extra = list(getattr(args, "skills_dir", None) or ())
    use_db = bool(getattr(args, "db", False))
    db_path = getattr(args, "db_path", None)
    return Ctx(
        sess=sess,
        m=Metrics(sess),
        skills=skills.collect(sess, extra),
        db=db.load(sess["meta"]["id"], db_path) if use_db else db.disabled(),
        args=args,
    )
