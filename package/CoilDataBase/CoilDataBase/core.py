from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import datetime
from .models import *
from sqlalchemy import create_engine


def get_engine(url='mysql+pymysql://root:nercar@localhost:3306/Coil'):
    engine = create_engine(url,
                           pool_size=20,
                           max_overflow=20,
                           pool_timeout=30,
                           pool_recycle=3600,
                           pool_pre_ping=True,
                           echo=False
                           )
    if not database_exists(engine.url):
        create_database(engine.url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

engine, Session = get_engine()