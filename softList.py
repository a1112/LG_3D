import winreg

keyDict = [
    "DisplayIcon",
    "DisplayName",
    "DisplayVersion",
    "InstallLocation",
    "UninstallString",
    "Publisher",
    "URLInfoAbout"
]

def enumerate_values(key_handle):
    i = 0
    res=[]
    while True:
        try:
            value = winreg.EnumValue(key_handle, i)
            # name, data, type = value
            res.append(value)
            i += 1
        except OSError:
            # 当索引超出范围时，将抛出OSError，表示没有更多的值
            break
    return res
def get_installed_programs_details():
    # 注册表中的路径   计算机\HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall
    path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    registry_key = winreg.HKEY_LOCAL_MACHINE

    with winreg.OpenKey(registry_key, path, 0, winreg.KEY_READ) as main_key:
        count_subkey = winreg.QueryInfoKey(main_key)[0]
        software_details_list = []
        for i in range(count_subkey):
            try:
                subkey_name = winreg.EnumKey(main_key, i)
                with winreg.OpenKey(main_key, subkey_name) as subkey:
                    keys = enumerate_values(subkey)
                    if keys:
                        software_details_list.append(keys)
            except EnvironmentError:
                continue  # 忽略无法读取的子键
    return software_details_list

programs_details = get_installed_programs_details()
