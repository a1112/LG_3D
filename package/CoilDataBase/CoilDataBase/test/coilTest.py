from CoilDataBase.core import get_engine
from CoilDataBase.models import Base

get_engine("sqlite:///CoilDataBase.db")

tables = [
    table.name for table in Base.metadata.tables.values()
]