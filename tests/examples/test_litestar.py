from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest
from litestar.testing import AsyncTestClient

from advanced_alchemy.base import UUIDBase
from advanced_alchemy.config import AsyncSessionConfig
from advanced_alchemy.extensions.litestar.plugins import SQLAlchemyAsyncConfig

if TYPE_CHECKING:
    from litestar import Litestar


@pytest.fixture()
async def test_client() -> AsyncIterator[AsyncTestClient[Litestar]]:
    # see _patch_bases in conftest.py
    from examples.litestar import init_app

    # Use an in-memory database for testing and create the tables.
    engine = SQLAlchemyAsyncConfig.create_engine_callable("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(UUIDBase.metadata.create_all)

    sqlalchemy_config = SQLAlchemyAsyncConfig(
        # Use the same session instance for all requests so the database doesn't disappear
        engine_instance=engine,
        session_config=AsyncSessionConfig(expire_on_commit=False),
    )

    app = init_app(sqlalchemy_config=sqlalchemy_config)
    app.debug = True

    async with AsyncTestClient(app=app) as client:
        yield client


async def test_create_list(test_client: AsyncTestClient[Litestar]) -> None:
    # see _patch_bases in conftest.py
    from examples.litestar import Author

    author = Author(name="foo")

    response = await test_client.post(
        "/authors",
        json=author.to_dict(),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == author.name

    response = await test_client.get("/authors")
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["name"] == author.name


async def test_create_get_update_delete(test_client: AsyncTestClient[Litestar]) -> None:
    # see _patch_bases in conftest.py
    from examples.litestar import Author

    author = Author(name="foo")

    response = await test_client.post(
        "/authors",
        json=author.to_dict(),
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == author.name
    author_id = response.json()["id"]

    response = await test_client.get(f"/authors/{author_id}")
    assert response.status_code == 200, response.text
    assert response.json()["name"] == author.name
    assert response.json()["id"] == author_id

    response = await test_client.patch(
        f"/authors/{author_id}",
        json={"name": "bar"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "bar"
    assert response.json()["id"] == author_id

    response = await test_client.delete(f"/authors/{author_id}")
    assert response.status_code == 204, response.text

    response = await test_client.get(f"/authors/{author_id}")
    assert response.status_code == 404, response.text
