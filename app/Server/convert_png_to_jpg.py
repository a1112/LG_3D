"""
将历史数据中的 preview/png 文件转换为 jpg 格式
现在所有文件都保存为 .jpg 格式，需要将旧的 .png 文件转换
"""
import os
import shutil
from pathlib import Path
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def convert_png_to_jpg(source_path: Path, quality: int = 85) -> bool:
    """
    将 PNG 文件转换为 JPG

    Args:
        source_path: PNG 文件路径
        quality: JPEG 质量 (1-100)

    Returns:
        是否成功转换
    """
    try:
        # 读取 PNG
        img = Image.open(source_path)

        # 处理透明通道
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为掩码
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 生成 JPG 路径
        jpg_path = source_path.with_suffix('.jpg')

        # 保存为 JPG
        img.save(jpg_path, quality=quality, optimize=True)

        logger.info("Converted: %s -> %s", source_path, jpg_path)
        return True

    except Exception as e:
        logger.error("Failed to convert %s: %s", source_path, e)
        return False


def migrate_directory(root_dir: Path, remove_png: bool = False) -> dict:
    """
    迁移目录中的所有 PNG 文件到 JPG

    Args:
        root_dir: 根目录（如 D:\Save_S）
        remove_png: 是否删除转换成功的 PNG 文件

    Returns:
        统计信息
    """
    stats = {
        'converted': 0,
        'skipped': 0,
        'failed': 0,
        'errors': []
    }

    if not root_dir.exists():
        logger.error("Directory not found: %s", root_dir)
        return stats

    # 查找所有 PNG 文件
    png_files = list(root_dir.rglob('*.png'))
    logger.info("Found %s PNG files in %s", len(png_files), root_dir)

    for png_path in png_files:
        # 跳过 mask 文件（这些需要保留 PNG 格式的透明通道）
        if 'mask' in png_path.parts or png_path.stem.endswith('MASK'):
            stats['skipped'] += 1
            continue

        # 检查是否已存在对应的 JPG 文件
        jpg_path = png_path.with_suffix('.jpg')
        if jpg_path.exists():
            stats['skipped'] += 1
            logger.debug("JPG already exists, skipping: %s", png_path)
            continue

        # 转换
        if convert_png_to_jpg(png_path):
            stats['converted'] += 1
            # 删除原 PNG 文件（可选）
            if remove_png:
                try:
                    png_path.unlink()
                    logger.info("Removed: %s", png_path)
                except Exception as e:
                    logger.error("Failed to remove %s: %s", png_path, e)
        else:
            stats['failed'] += 1
            stats['errors'].append(str(png_path))

    return stats


def main():
    """
    主函数：处理 Save_S 目录中的 PNG 文件
    """
    # 默认目录
    save_s_dir = Path(r"D:\Save_S")

    # 检查目录是否存在
    if not save_s_dir.exists():
        # 尝试从环境变量或配置文件获取
        logger.error("Default directory not found: %s", save_s_dir)
        logger.info("Please specify the correct directory in the script")
        return

    logger.info("Starting PNG to JPG migration for: %s", save_s_dir)
    logger.info("=" * 50)

    # 执行迁移（不删除原 PNG 文件，确认无误后再手动删除）
    stats = migrate_directory(save_s_dir, remove_png=False)

    logger.info("=" * 50)
    logger.info("Migration Summary:")
    logger.info("  Converted: %s", stats['converted'])
    logger.info("  Skipped:   %s", stats['skipped'])
    logger.info("  Failed:    %s", stats['failed'])

    if stats['errors']:
        logger.warning("Failed files (%s):", len(stats['errors']))
        for err in stats['errors'][:10]:  # 只显示前 10 个
            logger.warning("  - %s", err)
        if len(stats['errors']) > 10:
            logger.warning("  ... and %s more", len(stats['errors']) - 10)

    logger.info("=" * 50)
    logger.info("Migration completed!")
    logger.info("Please verify the converted files, then run again with remove_png=True to delete old PNG files")


if __name__ == "__main__":
    main()
