import inspect
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

from service.infrastructure.database.postgresql import PgConnector
from service.repositories.exceptions import (
    RepositoryError,
    RepositoryIntegrityError,
    RepositoryMultipleResultsError,
    RepositoryNotFoundError,
    RepositoryOperationalError,
)
from service.utils.logger import get_logger
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound, OperationalError

logger = get_logger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


def connection() -> (
    Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]
):
    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        signature = inspect.signature(func)
        accepts_session_param = "session" in signature.parameters
        accepts_kwargs = any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
        )

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:

            self_instance = args[0]
            if not hasattr(self_instance, "connector"):
                raise AttributeError("Instance must have 'connector' attribute")

            connector: PgConnector = getattr(self_instance, "connector")

            provided_session = kwargs.get("session")
            if provided_session is not None:
                session = provided_session
                manage_session = False
                session_ctx = None
            else:
                session_ctx = connector.get_session_context()
                session = await session_ctx.__aenter__()
                manage_session = True

            had_session = hasattr(self_instance, "session")
            previous_session = getattr(self_instance, "session", None)
            setattr(self_instance, "session", session)
            try:
                if accepts_session_param or accepts_kwargs:
                    kwargs["session"] = session

                result = await func(*args, **kwargs)

                if manage_session:
                    await session.commit()
                return result

            except IntegrityError as exc:
                if manage_session:
                    await session.rollback()
                logger.exception("Data integrity violation")
                raise RepositoryIntegrityError("Uniqueness violation") from exc

            except NoResultFound as exc:
                if manage_session:
                    await session.rollback()
                logger.warning("Record not found: %s", exc)
                raise RepositoryNotFoundError("Record not found") from exc

            except MultipleResultsFound as exc:
                if manage_session:
                    await session.rollback()
                logger.exception("Multiple records found")
                raise RepositoryMultipleResultsError() from exc

            except OperationalError as exc:
                if manage_session:
                    await session.rollback()
                logger.exception("Database connection error")
                raise RepositoryOperationalError("Database unavailable") from exc

            except Exception as exc:
                if manage_session:
                    await session.rollback()
                logger.exception("Unexpected error occurred")
                raise RepositoryError("Internal repository error") from exc

            finally:
                if manage_session:
                    await session_ctx.__aexit__(None, None, None)
                if had_session:
                    setattr(self_instance, "session", previous_session)
                else:
                    try:
                        delattr(self_instance, "session")
                    except AttributeError:
                        pass

        return wrapper

    return decorator
