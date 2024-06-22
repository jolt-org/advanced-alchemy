from __future__ import annotations

from typing import Any, Generator, cast

import pytest
from sqlalchemy import Engine, create_engine, insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from advanced_alchemy import base
from tests.fixtures import types


@pytest.fixture(scope="module")
def _patch_bases(monkeysession: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Ensure new registry state for every test.

    This prevents errors such as "Table '...' is already defined for
    this MetaData instance...
    """
    from sqlalchemy.orm import DeclarativeBase

    from advanced_alchemy import base

    class NewUUIDBase(base.UUIDPrimaryKey, base.CommonTableAttributes, DeclarativeBase): ...

    class NewUUIDAuditBase(
        base.UUIDPrimaryKey,
        base.CommonTableAttributes,
        base.AuditColumns,
        DeclarativeBase,
    ): ...

    class NewUUIDv6Base(base.UUIDPrimaryKey, base.CommonTableAttributes, DeclarativeBase): ...

    class NewUUIDv6AuditBase(
        base.UUIDPrimaryKey,
        base.CommonTableAttributes,
        base.AuditColumns,
        DeclarativeBase,
    ): ...

    class NewUUIDv7Base(base.UUIDPrimaryKey, base.CommonTableAttributes, DeclarativeBase): ...

    class NewUUIDv7AuditBase(
        base.UUIDPrimaryKey,
        base.CommonTableAttributes,
        base.AuditColumns,
        DeclarativeBase,
    ): ...

    class NewBigIntBase(base.BigIntPrimaryKey, base.CommonTableAttributes, DeclarativeBase): ...

    class NewBigIntAuditBase(base.BigIntPrimaryKey, base.CommonTableAttributes, base.AuditColumns, DeclarativeBase): ...

    monkeysession.setattr(base, "UUIDBase", NewUUIDBase)
    monkeysession.setattr(base, "UUIDAuditBase", NewUUIDAuditBase)
    monkeysession.setattr(base, "UUIDv6Base", NewUUIDv6Base)
    monkeysession.setattr(base, "UUIDv6AuditBase", NewUUIDv6AuditBase)
    monkeysession.setattr(base, "UUIDv7Base", NewUUIDv7Base)
    monkeysession.setattr(base, "UUIDv7AuditBase", NewUUIDv7AuditBase)
    monkeysession.setattr(base, "BigIntBase", NewBigIntBase)
    monkeysession.setattr(base, "BigIntAuditBase", NewBigIntAuditBase)


@pytest.fixture(name="engine", scope="module")
def duckdb_engine(
    _patch_bases: Any,
    tmpdir_factory: pytest.TempdirFactory,
) -> Generator[Engine, None, None]:
    """SQLite engine for end-to-end testing.

    Returns:
        Async SQLAlchemy engine instance.
    """
    tmp_path = tmpdir_factory.mktemp("data")  # pyright: ignore[reportAssignmentType]
    engine = create_engine(f"duckdb:///{tmp_path}/test.duck.db")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def initialize_database(
    engine: Engine,
) -> Generator[None, None, None]:
    with engine.begin() as conn:
        base.orm_registry.metadata.drop_all(conn)
        base.orm_registry.metadata.create_all(conn)
    yield


@pytest.fixture(name="sessionmaker", scope="module")
def session_maker_factory(engine: Engine) -> Generator[sessionmaker[Session], None, None]:
    yield sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(name="session")
def session(
    sessionmaker: sessionmaker[Session],
    initialize_database: None,
    raw_authors: types.RawRecordData,
    raw_slug_books: types.RawRecordData,
    raw_rules: types.RawRecordData,
    raw_secrets: types.RawRecordData,
    author_model: types.AuthorModel,
    model_with_fetched_value: types.ModelWithFetchedValue,
    item_model: types.ItemModel,
    tag_model: types.TagModel,
    book_model: types.BookModel,
    rule_model: types.RuleModel,
    secret_model: types.SecretModel,
    slug_book_model: types.SlugBookModel,
) -> Generator[Session, None, None]:
    models_and_data = (
        (rule_model, raw_rules),
        (book_model, None),
        (tag_model, None),
        (item_model, None),
        (model_with_fetched_value, None),
        (secret_model, raw_secrets),
        (slug_book_model, raw_slug_books),
        (author_model, raw_authors),
    )

    with sessionmaker() as session:
        try:
            for model, raw_models in models_and_data:
                if raw_models is not None:
                    session.execute(text(f"truncate table {model.__tablename__} cascade;"))
                    session.execute(insert(model).values(raw_models))
            session.commit()
            session.begin()
            yield session

        finally:
            session.rollback()


@pytest.fixture(name="any_session", params=["session"], ids=["Sync"])
def any_session(request: pytest.FixtureRequest) -> Generator[Session, None, None]:
    yield request.getfixturevalue(request.param)


@pytest.fixture()
def author_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.AuthorRepository:
    """Return an AuthorAsyncRepository or AuthorSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.AuthorAsyncRepository(session=any_session)
    else:
        repo = repository_module.AuthorSyncRepository(session=any_session)
    return cast(types.AuthorRepository, repo)


@pytest.fixture()
def secret_repo(
    request: pytest.FixtureRequest,
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.SecretRepository:
    """Return an SecretAsyncRepository or SecretSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.SecretAsyncRepository(session=any_session)
    else:
        repo = repository_module.SecretSyncRepository(session=any_session)
    return cast(types.SecretRepository, repo)


@pytest.fixture()
def author_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.AuthorService:
    """Return an AuthorAsyncService or AuthorSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = service_module.AuthorAsyncService(session=any_session)
    else:
        repo = service_module.AuthorSyncService(session=any_session)
    return cast(types.AuthorService, repo)


@pytest.fixture()
def rule_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.RuleRepository:
    """Return an RuleAsyncRepository or RuleSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.RuleAsyncRepository(session=any_session)
    else:
        repo = repository_module.RuleSyncRepository(session=any_session)
    return cast(types.RuleRepository, repo)


@pytest.fixture()
def rule_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.RuleService:
    """Return an RuleAsyncService or RuleSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = service_module.RuleAsyncService(session=any_session)
    else:
        repo = service_module.RuleSyncService(session=any_session)
    return cast(types.RuleService, repo)


@pytest.fixture()
def book_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.BookRepository:
    """Return an BookAsyncRepository or BookSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.BookAsyncRepository(session=any_session)
    else:
        repo = repository_module.BookSyncRepository(session=any_session)
    return cast(types.BookRepository, repo)


@pytest.fixture()
def book_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.BookService:
    """Return an BookAsyncService or BookSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = service_module.BookAsyncService(session=any_session)
    else:
        repo = service_module.BookSyncService(session=any_session)
    return cast(types.BookService, repo)


@pytest.fixture()
def slug_book_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.SlugBookRepository:
    """Return an SlugBookAsyncRepository or SlugBookSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.SlugBookAsyncRepository(session=any_session)
    else:
        repo = repository_module.SlugBookSyncRepository(session=any_session)
    return cast("types.SlugBookRepository", repo)


@pytest.fixture()
def slug_book_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.SlugBookService:
    """Return an SlugBookAsyncService or SlugBookSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        svc = service_module.SlugBookAsyncService(session=any_session)
    else:
        svc = service_module.SlugBookSyncService(session=any_session)
    return cast("types.SlugBookService", svc)


@pytest.fixture()
def tag_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.ItemRepository:
    """Return an TagAsyncRepository or TagSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.TagAsyncRepository(session=any_session)
    else:
        repo = repository_module.TagSyncRepository(session=any_session)

    return cast(types.ItemRepository, repo)


@pytest.fixture()
def tag_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.TagService:
    """Return an TagAsyncService or TagSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = service_module.TagAsyncService(session=any_session)
    else:
        repo = service_module.TagSyncService(session=any_session)
    return cast(types.TagService, repo)


@pytest.fixture()
def item_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.ItemRepository:
    """Return an ItemAsyncRepository or ItemSyncRepository based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ItemAsyncRepository(session=any_session)
    else:
        repo = repository_module.ItemSyncRepository(session=any_session)

    return cast(types.ItemRepository, repo)


@pytest.fixture()
def item_service(
    any_session: AsyncSession | Session,
    service_module: Any,
) -> types.ItemService:
    """Return an ItemAsyncService or ItemSyncService based on the current PK and session type"""
    if isinstance(any_session, AsyncSession):
        repo = service_module.ItemAsyncService(session=any_session)
    else:
        repo = service_module.ItemSyncService(session=any_session)
    return cast(types.ItemService, repo)


@pytest.fixture()
def model_with_fetched_value_repo(
    any_session: AsyncSession | Session,
    repository_module: Any,
) -> types.ModelWithFetchedValueRepository:
    """Return an ModelWithFetchedValueAsyncRepository or ModelWithFetchedValueSyncRepository
    based on the current PK and session type
    """
    if isinstance(any_session, AsyncSession):
        repo = repository_module.ModelWithFetchedValueAsyncRepository(session=any_session)
    else:
        repo = repository_module.ModelWithFetchedValueSyncRepository(session=any_session)
    return cast(types.ModelWithFetchedValueRepository, repo)
