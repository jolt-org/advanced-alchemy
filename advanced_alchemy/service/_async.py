"""Service object implementation for SQLAlchemy.

RepositoryService object is generic on the domain model type which
should be a SQLAlchemy model.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Generic, Iterable, cast, overload

from sqlalchemy import Select
from typing_extensions import Self

from advanced_alchemy.exceptions import AdvancedAlchemyError, RepositoryError
from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository._util import model_from_dict
from advanced_alchemy.repository.typing import ModelT
from advanced_alchemy.service.pagination import OffsetPagination

from ._converters import to_schema

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy import RowMapping, Select, StatementLambdaElement
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.ext.asyncio.scoping import async_scoped_session
    from sqlalchemy.orm import InstrumentedAttribute
    from sqlalchemy.sql import ColumnElement

    from advanced_alchemy.config.asyncio import SQLAlchemyAsyncConfig
    from advanced_alchemy.filters import FilterTypes
    from advanced_alchemy.repository import SQLAlchemyAsyncRepository
    from advanced_alchemy.repository.memory import SQLAlchemyAsyncMockRepository
    from advanced_alchemy.service.typing import FilterTypeT, ModelDTOT


class SQLAlchemyAsyncRepositoryReadService(Generic[ModelT]):
    """Service object that operates on a repository object."""

    repository_type: type[SQLAlchemyAsyncRepository[ModelT] | SQLAlchemyAsyncMockRepository[ModelT]]
    match_fields: list[str] | str | None = None

    def __init__(
        self,
        session: AsyncSession | async_scoped_session[AsyncSession],
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        auto_expunge: bool = False,
        auto_refresh: bool = True,
        auto_commit: bool = False,
        **repo_kwargs: Any,
    ) -> None:
        """Configure the service object.

        Args:
            session: Session managing the unit-of-work for the operation.
            statement: To facilitate customization of the underlying select query.
            auto_expunge: Remove object from session before returning.
            auto_refresh: Refresh object from session before returning.
            auto_commit: Commit objects before returning.
            **repo_kwargs: passed as keyword args to repo instantiation.
        """
        self.repository = self.repository_type(
            session=session,
            statement=statement,
            auto_expunge=auto_expunge,
            auto_refresh=auto_refresh,
            auto_commit=auto_commit,
            **repo_kwargs,
        )

    async def count(
        self,
        *filters: FilterTypes | ColumnElement[bool],
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        **kwargs: Any,
    ) -> int:
        """Count of records returned by query.

        Args:
            *filters: arguments for filtering.
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            **kwargs: key value pairs of filter types.

        Returns:
           A count of the collection, filtered, but ignoring pagination.
        """
        return await self.repository.count(*filters, statement=statement, **kwargs)

    async def exists(self, *filters: FilterTypes | ColumnElement[bool], **kwargs: Any) -> bool:
        """Wrap repository exists operation.

        Args:
            *filters: Types for specific filtering operations.
            **kwargs: Keyword arguments for attribute based filtering.

        Returns:
            Representation of instance with identifier `item_id`.
        """
        return await self.repository.exists(*filters, **kwargs)

    async def get(
        self,
        item_id: Any,
        auto_expunge: bool | None = None,
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        id_attribute: str | InstrumentedAttribute | None = None,
    ) -> ModelT:
        """Wrap repository scalar operation.

        Args:
            item_id: Identifier of instance to be retrieved.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            id_attribute: Allows customization of the unique identifier to use for model fetching.
                Defaults to `id`, but can reference any surrogate or candidate key for the table.


        Returns:
            Representation of instance with identifier `item_id`.
        """
        return await self.repository.get(
            item_id=item_id,
            auto_expunge=auto_expunge,
            statement=statement,
            id_attribute=id_attribute,
        )

    async def get_one(
        self,
        auto_expunge: bool | None = None,
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        **kwargs: Any,
    ) -> ModelT:
        """Wrap repository scalar operation.

        Args:
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            Representation of instance with identifier `item_id`.
        """
        return await self.repository.get_one(auto_expunge=auto_expunge, statement=statement, **kwargs)

    async def get_one_or_none(
        self,
        auto_expunge: bool | None = None,
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        **kwargs: Any,
    ) -> ModelT | None:
        """Wrap repository scalar operation.

        Args:
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            Representation of instance with identifier `item_id`.
        """
        return await self.repository.get_one_or_none(auto_expunge=auto_expunge, statement=statement, **kwargs)

    async def to_model(self, data: ModelT | dict[str, Any], operation: str | None = None) -> ModelT:
        """Parse and Convert input into a model.

        Args:
            data: Representations to be created.
            operation: Optional operation flag so that you can provide behavior based on CRUD operation
        Returns:
            Representation of created instances.
        """
        if isinstance(data, dict):
            return model_from_dict(model=self.repository.model_type, **data)  # type: ignore  # noqa: PGH003
        return data

    async def list_and_count(
        self,
        *filters: FilterTypes | ColumnElement[bool],
        auto_expunge: bool | None = None,
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        force_basic_query_mode: bool | None = None,
        **kwargs: Any,
    ) -> tuple[Sequence[ModelT], int]:
        """List of records and total count returned by query.

        Args:
            *filters: Types for specific filtering operations.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            force_basic_query_mode: Force list and count to use two queries instead of an analytical window function.
            **kwargs: Instance attribute value filters.

        Returns:
            List of instances and count of total collection, ignoring pagination.
        """
        return await self.repository.list_and_count(
            *filters,
            statement=statement,
            auto_expunge=auto_expunge,
            force_basic_query_mode=force_basic_query_mode,
            **kwargs,
        )

    @classmethod
    @asynccontextmanager
    async def new(
        cls,
        session: AsyncSession | async_scoped_session[AsyncSession],
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        config: SQLAlchemyAsyncConfig | None = None,
    ) -> AsyncIterator[Self]:
        """Context manager that returns instance of service object.

        Handles construction of the database session._create_select_for_model

        Returns:
            The service object instance.
        """
        if not config and not session:
            raise AdvancedAlchemyError(detail="Please supply an optional configuration or session to use.")

        if session:
            yield cls(statement=statement, session=session)
        elif config:
            async with config.get_session() as db_session:
                yield cls(
                    statement=statement,
                    session=db_session,
                )

    @overload
    def to_dto(self, data: ModelT) -> ModelT: ...

    @overload
    def to_dto(
        self,
        data: Sequence[ModelT],
        total: int | None = None,
        *filters: FilterTypes | ColumnElement[bool],
    ) -> OffsetPagination[ModelT]: ...

    def to_dto(
        self,
        data: ModelT | Sequence[ModelT],
        total: int | None = None,
        *filters: FilterTypes | ColumnElement[bool],
    ) -> ModelT | OffsetPagination[ModelT]:
        """Convert the object to a format expected by a DTO handler

        Args:
            data: The return from one of the service calls.
            total: the total number of rows in the data
            *filters: Collection route filters.

        Returns:
            The list of instances retrieved from the repository.
        """
        if not isinstance(data, Sequence | list):
            return data
        limit_offset = self.find_filter(LimitOffset, *filters)
        total = total or len(data)
        limit_offset = limit_offset if limit_offset is not None else LimitOffset(limit=len(data), offset=0)
        return OffsetPagination(
            items=list(data),
            limit=limit_offset.limit,
            offset=limit_offset.offset,
            total=total,
        )

    @overload
    def to_schema(self, dto: type[ModelDTOT], data: ModelT | RowMapping) -> ModelDTOT: ...

    @overload
    def to_schema(
        self,
        dto: type[ModelDTOT],
        data: Sequence[ModelT] | list[RowMapping],
        total: int | None = None,
        *filters: FilterTypes,
    ) -> OffsetPagination[ModelDTOT]: ...

    def to_schema(
        self,
        dto: type[ModelDTOT],
        data: ModelT | Sequence[ModelT] | list[RowMapping] | RowMapping,
        total: int | None = None,
        *filters: FilterTypes,
    ) -> ModelDTOT | OffsetPagination[ModelDTOT]:
        """Convert the object to a response schema.

        Args:
            dto: Collection route filters.
            data: The return from one of the service calls.
            total: the total number of rows in the data
            *filters: Collection route filters.

        Returns:
            The list of instances retrieved from the repository.
        """
        return to_schema(dto, data, total, *filters)

    async def list(
        self,
        *filters: FilterTypes | ColumnElement[bool],
        auto_expunge: bool | None = None,
        statement: Select[tuple[ModelT]] | StatementLambdaElement | None = None,
        **kwargs: Any,
    ) -> Sequence[ModelT]:
        """Wrap repository scalars operation.

        Args:
            *filters: Types for specific filtering operations.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`
            statement: To facilitate customization of the underlying select query.
                Defaults to :class:`SQLAlchemyAsyncRepository.statement <SQLAlchemyAsyncRepository>`
            **kwargs: Instance attribute value filters.

        Returns:
            The list of instances retrieved from the repository.
        """
        return await self.repository.list(*filters, statement=statement, auto_expunge=auto_expunge, **kwargs)

    @staticmethod
    def find_filter(
        filter_type: type[FilterTypeT],
        *filters: FilterTypes | ColumnElement[bool],
    ) -> FilterTypeT | None:
        """Get the filter specified by filter type from the filters.

        Args:
            filter_type: The type of filter to find.
            *filters: filter types to apply to the query

        Returns:
            The match filter instance or None
        """
        return next(
            (cast("FilterTypeT | None", filter_) for filter_ in filters if isinstance(filter_, filter_type)),
            None,
        )


class SQLAlchemyAsyncRepositoryService(SQLAlchemyAsyncRepositoryReadService[ModelT]):
    """Service object that operates on a repository object."""

    async def create(
        self,
        data: ModelT | dict[str, Any],
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        auto_refresh: bool | None = None,
    ) -> ModelT:
        """Wrap repository instance creation.

        Args:
            data: Representation to be created.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_refresh: Refresh object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_refresh <SQLAlchemyAsyncRepository>`
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
        Returns:
            Representation of created instance.
        """
        data = await self.to_model(data, "create")
        return await self.repository.add(
            data=data,
            auto_commit=auto_commit,
            auto_expunge=auto_expunge,
            auto_refresh=auto_refresh,
        )

    async def create_many(
        self,
        data: list[ModelT | dict[str, Any]] | list[dict[str, Any]] | list[ModelT],
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
    ) -> Sequence[ModelT]:
        """Wrap repository bulk instance creation.

        Args:
            data: Representations to be created.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`

        Returns:
            Representation of created instances.
        """
        data = [(await self.to_model(datum, "create")) for datum in data]
        return await self.repository.add_many(data=data, auto_commit=auto_commit, auto_expunge=auto_expunge)

    async def update(
        self,
        data: ModelT | dict[str, Any],
        item_id: Any | None = None,
        attribute_names: Iterable[str] | None = None,
        with_for_update: bool | None = None,
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        auto_refresh: bool | None = None,
        id_attribute: str | InstrumentedAttribute | None = None,
    ) -> ModelT:
        """Wrap repository update operation.

        Args:
            data: Representation to be updated.
            item_id: Identifier of item to be updated.
            attribute_names: an iterable of attribute names to pass into the ``update``
                method.
            with_for_update: indicating FOR UPDATE should be used, or may be a
                dictionary containing flags to indicate a more specific set of
                FOR UPDATE flags for the SELECT
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_refresh: Refresh object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_refresh <SQLAlchemyAsyncRepository>`
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            id_attribute: Allows customization of the unique identifier to use for model fetching.
                Defaults to `id`, but can reference any surrogate or candidate key for the table.

        Returns:
            Updated representation.
        """
        data = await self.to_model(data, "update")
        if (
            item_id is None
            and self.repository.get_id_attribute_value(
                item=data,
                id_attribute=id_attribute,
            )
            is None
        ):
            msg = (
                "Could not identify ID attribute value.  One of the following is required: "
                f"``item_id`` or ``data.{id_attribute or self.repository.id_attribute}``"
            )
            raise RepositoryError(msg)
        if item_id is not None:
            data = self.repository.set_id_attribute_value(item_id=item_id, item=data, id_attribute=id_attribute)
        return await self.repository.update(
            data=data,
            attribute_names=attribute_names,
            with_for_update=with_for_update,
            auto_expunge=auto_expunge,
            auto_commit=auto_commit,
            auto_refresh=auto_refresh,
            id_attribute=id_attribute,
        )

    async def update_many(
        self,
        data: list[ModelT | dict[str, Any]] | list[dict[str, Any]] | list[ModelT],
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
    ) -> Sequence[ModelT]:
        """Wrap repository bulk instance update.

        Args:
            data: Representations to be updated.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`

        Returns:
            Representation of updated instances.
        """
        data = [(await self.to_model(datum, "update")) for datum in data]
        return await self.repository.update_many(data, auto_commit=auto_commit, auto_expunge=auto_expunge)

    async def upsert(
        self,
        data: ModelT | dict[str, Any],
        item_id: Any | None = None,
        attribute_names: Iterable[str] | None = None,
        with_for_update: bool | None = None,
        auto_expunge: bool | None = None,
        auto_commit: bool | None = None,
        auto_refresh: bool | None = None,
        match_fields: list[str] | str | None = None,
    ) -> ModelT:
        """Wrap repository upsert operation.

        Args:
            data: Instance to update existing, or be created. Identifier used to determine if an
                existing instance exists is the value of an attribute on `data` named as value of
                `self.id_attribute`.
            item_id: Identifier of the object for upsert.
            attribute_names: an iterable of attribute names to pass into the ``update`` method.
            with_for_update: indicating FOR UPDATE should be used, or may be a
                dictionary containing flags to indicate a more specific set of
                FOR UPDATE flags for the SELECT
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_refresh: Refresh object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_refresh <SQLAlchemyAsyncRepository>`
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            match_fields: a list of keys to use to match the existing model.  When
                empty, all fields are matched.

        Returns:
            Updated or created representation.
        """
        data = await self.to_model(data, "upsert")
        item_id = item_id if item_id is not None else self.repository.get_id_attribute_value(item=data)
        if item_id is not None:
            self.repository.set_id_attribute_value(item_id, data)
        return await self.repository.upsert(
            data=data,
            attribute_names=attribute_names,
            with_for_update=with_for_update,
            auto_expunge=auto_expunge,
            auto_commit=auto_commit,
            auto_refresh=auto_refresh,
            match_fields=match_fields,
        )

    async def upsert_many(
        self,
        data: list[ModelT | dict[str, Any]] | list[dict[str, Any]] | list[ModelT],
        auto_expunge: bool | None = None,
        auto_commit: bool | None = None,
        no_merge: bool = False,
        match_fields: list[str] | str | None = None,
    ) -> list[ModelT]:
        """Wrap repository upsert operation.

        Args:
            data: Instance to update existing, or be created. Identifier used to determine if an
                existing instance exists is the value of an attribute on ``data`` named as value of
                :attr:`~advanced_alchemy.repository.AbstractAsyncRepository.id_attribute`.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            no_merge: Skip the usage of optimized Merge statements
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            match_fields: a list of keys to use to match the existing model.  When
                empty, all fields are matched.

        Returns:
            Updated or created representation.
        """
        data = [(await self.to_model(datum, "upsert")) for datum in data]
        return await self.repository.upsert_many(
            data=data,
            auto_expunge=auto_expunge,
            auto_commit=auto_commit,
            no_merge=no_merge,
            match_fields=match_fields,
        )

    async def get_or_upsert(
        self,
        match_fields: list[str] | str | None = None,
        upsert: bool = True,
        attribute_names: Iterable[str] | None = None,
        with_for_update: bool | None = None,
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        auto_refresh: bool | None = None,
        **kwargs: Any,
    ) -> tuple[ModelT, bool]:
        """Wrap repository instance creation.

        Args:
            match_fields: a list of keys to use to match the existing model.  When
                empty, all fields are matched.
            upsert: When using match_fields and actual model values differ from
                `kwargs`, perform an update operation on the model.
            create: Should a model be created.  If no model is found, an exception is raised.
            attribute_names: an iterable of attribute names to pass into the ``update``
                method.
            with_for_update: indicating FOR UPDATE should be used, or may be a
                dictionary containing flags to indicate a more specific set of
                FOR UPDATE flags for the SELECT
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_refresh: Refresh object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_refresh <SQLAlchemyAsyncRepository>`
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            Representation of created instance.
        """
        match_fields = match_fields or self.match_fields
        validated_model = await self.to_model(kwargs, "create")
        return await self.repository.get_or_upsert(
            match_fields=match_fields,
            upsert=upsert,
            attribute_names=attribute_names,
            with_for_update=with_for_update,
            auto_commit=auto_commit,
            auto_expunge=auto_expunge,
            auto_refresh=auto_refresh,
            **validated_model.to_dict(),
        )

    async def get_and_update(
        self,
        match_fields: list[str] | str | None = None,
        attribute_names: Iterable[str] | None = None,
        with_for_update: bool | None = None,
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        auto_refresh: bool | None = None,
        **kwargs: Any,
    ) -> tuple[ModelT, bool]:
        """Wrap repository instance creation.

        Args:
            match_fields: a list of keys to use to match the existing model.  When
                empty, all fields are matched.
            attribute_names: an iterable of attribute names to pass into the ``update``
                method.
            with_for_update: indicating FOR UPDATE should be used, or may be a
                dictionary containing flags to indicate a more specific set of
                FOR UPDATE flags for the SELECT
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_refresh: Refresh object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_refresh <SQLAlchemyAsyncRepository>`
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            **kwargs: Identifier of the instance to be retrieved.

        Returns:
            Representation of updated instance.
        """
        match_fields = match_fields or self.match_fields
        validated_model = await self.to_model(kwargs, "update")
        return await self.repository.get_and_update(
            match_fields=match_fields,
            attribute_names=attribute_names,
            with_for_update=with_for_update,
            auto_commit=auto_commit,
            auto_expunge=auto_expunge,
            auto_refresh=auto_refresh,
            **validated_model.to_dict(),
        )

    async def delete(
        self,
        item_id: Any,
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        id_attribute: str | InstrumentedAttribute | None = None,
    ) -> ModelT:
        """Wrap repository delete operation.

        Args:
            item_id: Identifier of instance to be deleted.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            id_attribute: Allows customization of the unique identifier to use for model fetching.
                Defaults to `id`, but can reference any surrogate or candidate key for the table.


        Returns:
            Representation of the deleted instance.
        """
        return await self.repository.delete(
            item_id=item_id,
            auto_commit=auto_commit,
            auto_expunge=auto_expunge,
            id_attribute=id_attribute,
        )

    async def delete_many(
        self,
        item_ids: list[Any],
        auto_commit: bool | None = None,
        auto_expunge: bool | None = None,
        id_attribute: str | InstrumentedAttribute | None = None,
        chunk_size: int | None = None,
    ) -> Sequence[ModelT]:
        """Wrap repository bulk instance deletion.

        Args:
            item_ids: Identifier of instance to be deleted.
            auto_expunge: Remove object from session before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_expunge <SQLAlchemyAsyncRepository>`.
            auto_commit: Commit objects before returning. Defaults to
                :class:`SQLAlchemyAsyncRepository.auto_commit <SQLAlchemyAsyncRepository>`
            id_attribute: Allows customization of the unique identifier to use for model fetching.
                Defaults to `id`, but can reference any surrogate or candidate key for the table.
            chunk_size: Allows customization of the ``insertmanyvalues_max_parameters`` setting for the driver.
                Defaults to `950` if left unset.


        Returns:
            Representation of removed instances.
        """
        return await self.repository.delete_many(
            item_ids=item_ids,
            auto_commit=auto_commit,
            auto_expunge=auto_expunge,
            id_attribute=id_attribute,
            chunk_size=chunk_size,
        )
