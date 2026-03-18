from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID

from service.infrastructure.database.postgresql import PgConnector
from service.repositories.decorators.session_processor import connection
from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, joinedload

T = TypeVar("T", bound=DeclarativeBase)


class PaginationResult:

    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        total_pages: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = total_pages
        self.has_next = page < total_pages
        self.has_prev = page > 1


class BaseRepository:
    """
    Базовый класс репозиториев с общими вспомогательными методами.

    Предоставляет generic CRUD операции, пагинацию, soft delete и query helpers.

    ## Использование декораторов в наследниках

    При создании конкретных репозиториев применяйте декораторы на уровне бизнес-методов:

    ### @cache - Кэширование часто читаемых данных
    ```python
    from service.repositories.decorators import cache

    @cache(ttl=300.0, namespace="users")
    @connection()
    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.get_one_or_none(self.session, User, User.email == email)
    ```

    **TTL рекомендации:**
    - 30-60s: изменчивые данные (сессии, заказы)
    - 120-300s: часто читаемые (профили, товары)
    - 600-1800s: стабильные данные (шаблоны, справочники)
    - 3600s: конфигурация (константы)

    ### @retry - Retry для внешних интеграций
    ```python
    from service.repositories.decorators import retry

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    @connection()
    async def create_external_webhook(self, url: str) -> Webhook:
        # Вызов внешнего API
        ...
    ```

    ### Комбинирование декораторов
    ```python
    @cache(ttl=120.0, namespace="products")
    @connection()
    async def get_products_by_category(self, category_id: UUID) -> list[Product]:
        # Кэширование для оптимизации сложных запросов
        ...
    ```

    **Порядок декораторов (сверху вниз):**
    1. @cache (внешний - проверяет кэш первым)
    2. @retry (повторяет при ошибках)
    3. @connection() (управляет сессией БД)
    """

    def __init__(self, connector: PgConnector) -> None:
        self._connector = connector

    @property
    def connector(self) -> PgConnector:
        return self._connector

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        async with self._connector.get_session_context() as session:
            yield session

    async def _execute(self, session: AsyncSession, statement):
        return await session.execute(statement)


    @connection()
    async def get_all(
        self,
        session: AsyncSession,
        model: Type[T],
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> List[T]:
        """
        Generic метод для получения всех записей модели.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            include_deleted: Включать ли soft-deleted записи

        Returns:
            List[T]: Список объектов модели
        """
        stmt = select(model)

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())


    @connection()
    async def get_by_ids(
        self,
        session: AsyncSession,
        model: Type[T],
        ids: List[Union[UUID, int]],
        include_deleted: bool = False,
    ) -> List[T]:
        """
        Bulk fetch записей по списку ID.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            ids: Список ID для поиска
            include_deleted: Включать ли soft-deleted записи

        Returns:
            List[T]: Список найденных объектов
        """
        if not ids:
            return []

        stmt = select(model).where(model.id.in_(ids))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        result = await session.execute(stmt)
        return list(result.scalars().all())


    @connection()
    async def bulk_create(
        self,
        session: AsyncSession,
        model: Type[T],
        items: List[Dict[str, Any]],
    ) -> List[T]:
        """
        Bulk insert записей.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            items: Список словарей с данными для создания

        Returns:
            List[T]: Список созданных объектов
        """
        if not items:
            return []

        instances = [model(**item) for item in items]
        session.add_all(instances)
        await session.flush()
        return instances


    @connection()
    async def bulk_update(
        self,
        session: AsyncSession,
        model: Type[T],
        updates: List[Dict[str, Any]],
    ) -> int:
        """
        Bulk update записей.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            updates: Список словарей с id и полями для обновления

        Returns:
            int: Количество обновленных записей
        """
        if not updates:
            return 0

        count = 0
        for item in updates:
            item_id = item.pop("id", None)
            if item_id:
                stmt = update(model).where(model.id == item_id).values(**item)
                result = await session.execute(stmt)
                count += result.rowcount

        return count


    @connection()
    async def bulk_delete(
        self,
        session: AsyncSession,
        model: Type[T],
        ids: List[Union[UUID, int]],
        soft: bool = True,
    ) -> int:
        """
        Bulk delete записей.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            ids: Список ID для удаления
            soft: Использовать soft delete если доступно

        Returns:
            int: Количество удаленных записей
        """
        if not ids:
            return 0

        if soft and hasattr(model, "deleted_at"):
            stmt = (
                update(model)
                .where(model.id.in_(ids))
                .where(model.deleted_at.is_(None))
                .values(deleted_at=datetime.now(timezone.utc))
            )
        else:
            stmt = delete(model).where(model.id.in_(ids))

        result = await session.execute(stmt)
        return result.rowcount


    @connection()
    async def exists(
        self,
        session: AsyncSession,
        model: Type[T],
        id: Union[UUID, int],
        include_deleted: bool = False,
    ) -> bool:
        """
        Проверить существование записи по ID.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            id: ID для проверки
            include_deleted: Проверять ли soft-deleted записи

        Returns:
            bool: True если запись существует
        """
        stmt = select(func.count()).select_from(model).where(model.id == id)

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        result = await session.execute(stmt)
        count = result.scalar()
        return count > 0


    @connection()
    async def count(
        self,
        session: AsyncSession,
        model: Type[T],
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Подсчитать количество записей с опциональными фильтрами.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            filters: Словарь фильтров {field: value}
            include_deleted: Включать ли soft-deleted записи

        Returns:
            int: Количество записей
        """
        stmt = select(func.count()).select_from(model)

        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(model, field):
                    conditions.append(getattr(model, field) == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        result = await session.execute(stmt)
        return result.scalar()


    @connection()
    async def get_one_or_none(
        self,
        session: AsyncSession,
        model: Type[T],
        filters: Dict[str, Any],
        include_deleted: bool = False,
    ) -> Optional[T]:
        """
        Generic single fetch с фильтрами.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            filters: Словарь фильтров {field: value}
            include_deleted: Включать ли soft-deleted записи

        Returns:
            Optional[T]: Объект модели или None
        """
        stmt = select(model)

        conditions = []
        for field, value in filters.items():
            if hasattr(model, field):
                conditions.append(getattr(model, field) == value)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

  
    @connection()
    async def paginate(
        self,
        session: AsyncSession,
        model: Type[T],
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        include_deleted: bool = False,
    ) -> PaginationResult:
        """
        Пагинация с offset-based подходом.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            page: Номер страницы (начиная с 1)
            page_size: Размер страницы
            filters: Опциональные фильтры
            order_by: Поле для сортировки
            order_desc: Сортировать по убыванию
            include_deleted: Включать ли soft-deleted записи

        Returns:
            PaginationResult: Объект с результатами пагинации
        """

        total = await self.count(
            session=session,
            model=model,
            filters=filters,
            include_deleted=include_deleted,
        )

        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size

        stmt = select(model)

        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(model, field):
                    conditions.append(getattr(model, field) == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        if order_by and hasattr(model, order_by):
            order_field = getattr(model, order_by)
            stmt = stmt.order_by(desc(order_field) if order_desc else order_field)
        elif hasattr(model, "created_at"):
            stmt = stmt.order_by(desc(model.created_at))

        stmt = stmt.limit(page_size).offset(offset)

        result = await session.execute(stmt)
        items = list(result.scalars().all())

        return PaginationResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


    @connection()
    async def soft_delete(
        self,
        session: AsyncSession,
        model: Type[T],
        id: Union[UUID, int],
    ) -> bool:
        """
        Мягкое удаление записи (установка deleted_at).

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            id: ID записи для удаления

        Returns:
            bool: True если запись была удалена
        """
        if not hasattr(model, "deleted_at"):
            raise AttributeError(f"Model {model.__name__} does not support soft delete")

        stmt = (
            update(model)
            .where(model.id == id)
            .where(model.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc))
        )

        result = await session.execute(stmt)
        return result.rowcount > 0


    @connection()
    async def restore(
        self,
        session: AsyncSession,
        model: Type[T],
        id: Union[UUID, int],
    ) -> bool:
        """
        Восстановление soft-deleted записи.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            id: ID записи для восстановления

        Returns:
            bool: True если запись была восстановлена
        """
        if not hasattr(model, "deleted_at"):
            raise AttributeError(f"Model {model.__name__} does not support soft delete")

        stmt = (
            update(model)
            .where(model.id == id)
            .where(model.deleted_at.isnot(None))
            .values(deleted_at=None)
        )

        result = await session.execute(stmt)
        return result.rowcount > 0


    @connection()
    async def force_delete(
        self,
        session: AsyncSession,
        model: Type[T],
        id: Union[UUID, int],
    ) -> bool:
        """
        Безвозвратное удаление записи из БД.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            id: ID записи для удаления

        Returns:
            bool: True если запись была удалена
        """
        stmt = delete(model).where(model.id == id)
        result = await session.execute(stmt)
        return result.rowcount > 0


    @connection()
    async def filter_by(
        self,
        session: AsyncSession,
        model: Type[T],
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        include_deleted: bool = False,
    ) -> List[T]:
        """
        Generic фильтрация с поддержкой пагинации и сортировки.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            filters: Словарь фильтров {field: value}
            limit: Максимальное количество записей
            offset: Смещение
            order_by: Поле для сортировки
            order_desc: Сортировать по убыванию
            include_deleted: Включать ли soft-deleted записи

        Returns:
            List[T]: Список отфильтрованных объектов
        """
        stmt = select(model)

        conditions = []
        for field, value in filters.items():
            if hasattr(model, field):
                if isinstance(value, list):
                    conditions.append(getattr(model, field).in_(value))
                else:
                    conditions.append(getattr(model, field) == value)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        if order_by and hasattr(model, order_by):
            order_field = getattr(model, order_by)
            stmt = stmt.order_by(desc(order_field) if order_desc else order_field)

        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())


    @connection()
    async def search(
        self,
        session: AsyncSession,
        model: Type[T],
        query: str,
        fields: List[str],
        limit: int = 50,
        include_deleted: bool = False,
    ) -> List[T]:
        """
        Full-text search helper (простой LIKE поиск по нескольким полям).

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            query: Строка поиска
            fields: Список полей для поиска
            limit: Максимальное количество результатов
            include_deleted: Включать ли soft-deleted записи

        Returns:
            List[T]: Список найденных объектов
        """
        stmt = select(model)

        search_conditions = []
        search_pattern = f"%{query}%"

        for field in fields:
            if hasattr(model, field):
                search_conditions.append(getattr(model, field).ilike(search_pattern))

        if search_conditions:
            stmt = stmt.where(or_(*search_conditions))

        if not include_deleted and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())


    @connection()
    async def get_or_create(
        self,
        session: AsyncSession,
        model: Type[T],
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> tuple[T, bool]:
        """
        Get or create pattern.

        Args:
            session: Асинхронная сессия БД
            model: SQLAlchemy модель
            defaults: Значения по умолчанию при создании
            **kwargs: Поля для поиска существующей записи

        Returns:
            tuple[T, bool]: (объект, created) где created=True если объект был создан
        """

        stmt = select(model)
        conditions = []
        for field, value in kwargs.items():
            if hasattr(model, field):
                conditions.append(getattr(model, field) == value)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))

        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance:
            return instance, False

        create_data = {**kwargs}
        if defaults:
            create_data.update(defaults)

        instance = model(**create_data)
        session.add(instance)
        await session.flush()

        return instance, True


    def _apply_eager_loading(self, stmt, *relationships):
        """
        Применить eager loading для relationships.

        Args:
            stmt: SQLAlchemy statement
            *relationships: Имена relationships для eager load

        Returns:
            statement с примененным joinedload
        """
        for rel in relationships:
            stmt = stmt.options(joinedload(rel))
        return stmt
