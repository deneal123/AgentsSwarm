import logging
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound, OperationalError

from service.infrastructure.database.postgresql import PgConnector
from service.shared.repositories.exceptions import (
    RepositoryError,
    RepositoryIntegrityError,
    RepositoryMultipleResultsError,
    RepositoryNotFoundError,
    RepositoryOperationalError,
)

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


def connection() -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:

            self_instance = args[0]
            if not hasattr(self_instance, "connector"):
                raise AttributeError("Instance must have 'connector' attribute")

            connector: PgConnector = self_instance.connector

            async with connector.get_session_context() as session:
                try:
                    if "session" not in kwargs:
                        kwargs["session"] = session
                    result = await func(*args, **kwargs)

                    await session.commit()
                    return result

                except IntegrityError as exc:
                    await session.rollback()
                    logger.exception("Data integrity violation")
                    raise RepositoryIntegrityError("Uniqueness violation") from exc

                except NoResultFound as exc:
                    await session.rollback()
                    logger.warning("Record not found: %s", exc)
                    raise RepositoryNotFoundError("Record not found") from exc

                except MultipleResultsFound as exc:
                    await session.rollback()
                    logger.exception("Multiple records found")
                    raise RepositoryMultipleResultsError() from exc

                except OperationalError as exc:
                    await session.rollback()
                    logger.exception("Database connection error")
                    raise RepositoryOperationalError("Database unavailable") from exc

                except Exception as exc:
                    await session.rollback()
                    logger.exception("Unexpected error occurred")
                    raise RepositoryError("Internal repository error") from exc

        return wrapper

    return decorator
