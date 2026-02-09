"""
移动 detection 目录到统一位置

从:
- D:\Save_S\{seq_no}\detection
- E:\Save_L\{seq_no}\detection

到:
- D:\detection\{seq_no}_S\
- D:\detection\{seq_no}_L\
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def move_detections():
    # 源目录
    sources = [
        (Path("D:/Save_S"), "_S"),
        (Path("E:/Save_L"), "_L"),
    ]

    # 目标根目录
    target_root = Path("D:/detection")
    target_root.mkdir(exist_ok=True)

    # 记录日志
    log_file = target_root / f"move_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    moved_count = 0
    skipped_count = 0
    error_count = 0

    with open(log_file, "w", encoding="utf-8") as log:
        log.write(f"开始时间: {datetime.now()}\n")
        log.write(f"目标目录: {target_root}\n\n")

        for source_base, suffix in sources:
            if not source_base.exists():
                log.write(f"[警告] 源目录不存在: {source_base}\n\n")
                continue

            log.write(f"扫描目录: {source_base}{suffix}\n")

            # 遍历所有子目录（卷材编号）
            for coil_folder in source_base.iterdir():
                if not coil_folder.is_dir():
                    continue

                seq_no = coil_folder.name
                detection_src = coil_folder / "detection"

                # 检查 detection 目录是否存在
                if not detection_src.exists():
                    skipped_count += 1
                    continue

                # 目标目录名：{seq_no}_S 或 {seq_no}_L
                target_name = f"{seq_no}{suffix}"
                target_dir = target_root / target_name

                # 如果目标已存在，添加序号
                counter = 1
                original_target = target_dir
                while target_dir.exists():
                    target_dir = target_root / f"{target_name}_{counter}"
                    counter += 1

                try:
                    # 移动目录
                    shutil.move(str(detection_src), str(target_dir))

                    moved_count += 1
                    log.write(f"  [移动] {seq_no} -> {target_dir.name}\n")
                    print(f"[移动] {detection_src} -> {target_dir}")

                except Exception as e:
                    error_count += 1
                    log.write(f"  [错误] {seq_no}: {e}\n")
                    print(f"[错误] {detection_src}: {e}")

            log.write(f"\n")

        # 写入汇总
        log.write(f"\n=== 汇总 ===\n")
        log.write(f"移动成功: {moved_count}\n")
        log.write(f"跳过(无detection): {skipped_count}\n")
        log.write(f"错误: {error_count}\n")
        log.write(f"结束时间: {datetime.now()}\n")

    print(f"\n=== 完成 ===")
    print(f"日志文件: {log_file}")
    print(f"移动成功: {moved_count}")
    print(f"跳过: {skipped_count}")
    print(f"错误: {error_count}")


if __name__ == "__main__":
    print("=" * 50)
    print("移动 detection 目录")
    print("=" * 50)
    print(f"源目录:")
    print(f"  - D:\\Save_S\\{{seq_no}}\\detection")
    print(f"  - E:\\Save_L\\{{seq_no}}\\detection")
    print(f"目标目录: D:\\detection")
    print("=" * 50)

    response = input("确认执行? (y/n): ")
    if response.lower() == 'y':
        move_detections()
    else:
        print("已取消")
