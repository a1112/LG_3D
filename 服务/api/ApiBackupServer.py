from CoilDataBase import backup
from .api_core import app
from Globs import serverConfigProperty


@app.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state = backup.save_to_sql(sql_file, mysqldump_exe=serverConfigProperty.mysqldump_exe)
    return {"state": state}
