from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


class ReadReplicaSessionFactory:
    """Route read-only work to a replica when configured."""

    def __init__(self) -> None:
        self.primary_url = settings.DATABASE_URL
        self.replica_url = settings.DATABASE_REPLICA_URL or settings.DATABASE_URL
        self._primary_engine = create_engine(self.primary_url)
        self._replica_engine = create_engine(self.replica_url)
        self._primary_session_factory = sessionmaker(bind=self._primary_engine, autocommit=False, autoflush=False)
        self._replica_session_factory = sessionmaker(bind=self._replica_engine, autocommit=False, autoflush=False)

    def primary_session(self):
        return self._primary_session_factory()

    def replica_session(self):
        return self._replica_session_factory()


read_replica_session_factory = ReadReplicaSessionFactory()
