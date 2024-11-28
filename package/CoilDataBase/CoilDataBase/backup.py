import subprocess


def backup_mysql_db(host, user, password, db_name, backup_file):
    # 构建 mysqldump 命令
    cmd = f"mysqldump -h {host} -u {user} -p{password} {db_name} > {backup_file}"

    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"MySQL 数据库 {db_name} 备份成功！")
    except subprocess.CalledProcessError as e:
        print(f"备份失败: {e}")


# 示例
# backup_mysql_db('localhost', 'root', 'password', 'my_database', 'my_database_backup.sql')
