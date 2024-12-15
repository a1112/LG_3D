import subprocess
from .config import Config


def get_mysqldump_cmd(save_file, mysqldump_exe="mysqldump"):
    return f'"{mysqldump_exe}"' + f" -u {Config.user} -p{Config.password} {Config.database} > " + f'"{save_file}"'


def save_to_sql(save_file, mysqldump_exe="mysqldump"):
    mysqldump_cmd = get_mysqldump_cmd(save_file, mysqldump_exe)
    try:
        subprocess.run(mysqldump_cmd, shell=True, check=True)
        print(f"MySQL 数据库 备份成功！ {mysqldump_cmd}")
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")


def backup_mysql_db(host, user, password, db_name, backup_file):
    # 构建 mysqldump 命令
    cmd = "mysqldump -u root -pnercar Coil > d:/Coil.sql"
    # cmd = f"mysqldump -h {host} -u {user} -p{password} {db_name} > {backup_file}"

    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"MySQL 数据库 {db_name} 备份成功！")
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")
