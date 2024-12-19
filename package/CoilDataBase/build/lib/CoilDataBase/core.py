from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from .config import get_url
from .models import *


def get_engine(url=None):
    if url is None:
        url = get_url()
    engine_ = create_engine(url,
                            pool_size=10,
                            max_overflow=10,
                            pool_timeout=20,
                            pool_recycle=600,
                            # pool_pre_ping=True,
                            echo=False
                            )
    if not database_exists(engine_.url):
        create_database(engine_.url)
    Base.metadata.create_all(engine_)
    return engine_, sessionmaker(bind=engine_)


engine, Session = get_engine()
