from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def _patch_bases(monkeypatch: MonkeyPatch) -> None:
    """
    Ensure metadata isn't shared with other tests.

    Within tests, imports that include SQLAlchemy models must be put into the
    test functions so that this monkeypatch effects them.  The joys of testing
    with global variables.
    """
    from sqlalchemy import orm
    from sqlalchemy.schema import MetaData

    class NewDeclarativeBase(orm.DeclarativeBase):
        metadata = MetaData()

    monkeypatch.setattr(orm, "DeclarativeBase", NewDeclarativeBase)
