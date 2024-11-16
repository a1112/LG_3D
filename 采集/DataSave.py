from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, BINARY, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()
from sqlalchemy_utils import database_exists, create_database
import datetime


class SecondaryCoil(Base):
    __tablename__ = 'SecondaryCoil'
    #   extend_existing=True
    Id = Column(Integer, primary_key=True, autoincrement=True)
    CoilNo = Column(String(20))
    CoilType = Column(String(20))
    CoilInside = Column(Float)  # 内径
    CoilDia = Column(Float)  # 卷径
    Thickness = Column(Float)
    Width = Column(Float)
    Weight = Column(Float)
    ActWidth = Column(Float)
    CreateTime = Column(DateTime, server_default=func.now())

    def get_json(self):
        return {
            "Id": self.Id,
            "CoilNo": self.CoilNo,
            "CoilType": self.CoilType,
            "CoilInside": self.CoilInside,
            "CoilDia": self.CoilDia,
            "Thickness": self.Thickness,
            "Width": self.Width,
            "Weight": self.Weight,
            "ActWidth": self.ActWidth,
            # "CreateTime": self.CreateTime
        }

    def __str__(self):
        return self.get_json().__str__()


engine = create_engine('mysql+pymysql://root:nercar@localhost:3306/Coil',
                       pool_size=10,
                       max_overflow=20,
                       pool_timeout=30,
                       pool_recycle=3600,
                       pool_pre_ping=True)
if not database_exists(engine.url):
    create_database(engine.url)
print(database_exists(engine.url))

Base.metadata.create_all(engine)
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)


def add_coil(coil):
    with Session() as session:
        session.add(SecondaryCoil(
            CoilNo=coil["Coil_ID"],
            CoilType=coil["Steel_Grade"],
            CoilInside=coil["coil_in_dia"],
            CoilDia=coil["coil_dia"],
            Thickness=coil["FM_Tar_Thickness"],
            Width=coil["FM_Tar_Width"],
            Weight=coil["sp01"][0],
            ActWidth=coil["act_w"],
            CreateTime=datetime.datetime.now()
        ))
        session.commit()


def get_last_coil():
    with Session() as session:
        return session.query(SecondaryCoil).order_by(SecondaryCoil.CreateTime.desc()).first()
