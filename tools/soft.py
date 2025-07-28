import os

import psutil


def get_process(pid):
    """检查指定PID的进程是否正在运行"""
    try:
        # 尝试获取进程信息
        proc = psutil.Process(pid)
        # 这里可以通过proc.status()检查进程状态，但简单判断存在性即可
        # 即使进程存在，它可能处于僵尸状态等，但通常我们认为存在就是运行
        return proc
    except psutil.NoSuchProcess:
        return None

def kill_process_and_children(pid):
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"进程 {pid} 不存在")
        return

    # 递归获取所有子进程
    children = parent.children(recursive=True)

    # 先终止子进程
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass

    # 终止父进程
    parent.terminate()

    # # 强制杀死残留进程（可选）
    # _, alive = psutil.wait_procs(children + [parent], timeout=5)
    # for p in alive:
    #     try:
    #         p.kill()
    #         print(f"强制杀死进程 {p.pid}")
    #     except psutil.NoSuchProcess:
    #         pass


def getProcessDict():
    process = getProcess()
    processDict = {}
    for pro in process:
        if "exe" in pro:
            processDict[os.path.normpath(pro["exe"])] = pro
            if pro["name"] == "cmd.exe":
                processDict[os.path.normpath(pro["cmdline"][-1]).strip()] = pro
    return processDict


def getProcess():
    all_processes_ = psutil.process_iter()
    all_processes_ = list(all_processes_)
    return [toDict(process) for process in all_processes_]


def toDict(process: psutil.Process):
    processDict = {}
    for attr in allAttrs:
        try:
            attrValue = getattr(process, attr)()
            processDict[attr] = attrValue
        except Exception as e:
            pass
    return processDict


allAttrs = ['pid', 'name', 'ppid',
            'username', 'create_time', 'cpu_percent',
            'memory_percent',
            'exe', 'cmdline', 'status', 'cwd'
            ]
