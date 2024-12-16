from CoilDataBase import backup
from .api_core import app
from Globs import serverConfigProperty


@app.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state=False
    if ".sql" in sql_file.lower():
        state = backup.backup_to_sql(sql_file, mysqldump_exe=serverConfigProperty.mysqldump_exe)
    if ".db" in sql_file.lower():
        state = backup.backup_to_sqlite(sql_file)
    return {"state": state}
