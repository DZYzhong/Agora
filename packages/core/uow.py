"""Application-level transaction boundary for SQLAlchemy commands."""

from types import TracebackType

from sqlalchemy.orm import SessionTransaction
from sqlalchemy.orm import Session


class SqlAlchemyUnitOfWork:
    _SESSION_INFO_KEY = "agora_active_unit_of_work"

    def __init__(self, session: Session):
        self.session = session
        self._transaction: SessionTransaction | None = None
        self._active = False
        self._committed = False

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        if self.session.info.get(self._SESSION_INFO_KEY) is not None:
            raise RuntimeError("Nested SqlAlchemyUnitOfWork is not supported")
        if self.session.in_transaction():
            raise RuntimeError("SqlAlchemyUnitOfWork cannot enter with an existing SQLAlchemy transaction")
        self._transaction = self.session.begin()
        self.session.info[self._SESSION_INFO_KEY] = self
        self._active = True
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            if self.session.info.get(self._SESSION_INFO_KEY) is self:
                self.session.info.pop(self._SESSION_INFO_KEY)
            self._transaction = None
            self._active = False
        return False

    def commit(self) -> None:
        self._ensure_active()
        self._ensure_transaction().commit()
        self._committed = True

    def rollback(self) -> None:
        self._ensure_active()
        transaction = self._ensure_transaction()
        if transaction.is_active:
            transaction.rollback()

    def flush(self) -> None:
        self._ensure_active()
        self.session.flush()

    def _ensure_active(self) -> None:
        if not self._active:
            raise RuntimeError("SqlAlchemyUnitOfWork is not active")

    def _ensure_transaction(self) -> SessionTransaction:
        if self._transaction is None:
            raise RuntimeError("SqlAlchemyUnitOfWork does not own a transaction")
        return self._transaction
