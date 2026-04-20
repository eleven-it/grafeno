"""
Fixtures de pytest para tests de integración con DB en memoria.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.domain.models import Base


@pytest.fixture(scope="function")
def db():
    """DB SQLite en memoria para tests de integración."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
