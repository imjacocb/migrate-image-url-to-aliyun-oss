import os
import re
import sys
import argparse

def rename_files_in_directory(target_dir, dry_run=True):
    """
    遍历目录，移除 .md 文件名开头的 YYYYMMDD- 前缀。

    :param target_dir: 目标目录路径
    :param dry_run: 如果为 True，只打印将要执行的操作，不实际重命名
    """
    # 正则表达式匹配以 8位数字开头，后跟一个横杠的文件名部分
    # ^(\d{8})- 匹配开头的8个数字和一个横杠
    pattern = re.compile(r'^(\d{8})-(.*)')

    if not os.path.isdir(target_dir):
        print(f"错误: 目录 '{target_dir}' 不存在或不是一个有效的目录。")
        return

    print(f"正在扫描目录: {target_dir}")
    print(f"模式: {'[模拟运行] ' if dry_run else ''}移除 .md 文件名开头的 YYYYMMDD- 前缀")
    print("-" * 50)

    renamed_count = 0

    # walk 遍历所有子目录
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            # 【新增】只处理 .md 文件
            if not filename.lower().endswith('.md'):
                continue

            match = pattern.match(filename)
            if match:
                # 获取去除前缀后的新文件名
                new_filename = match.group(2)

                old_path = os.path.join(root, filename)
                new_path = os.path.join(root, new_filename)

                # 检查新文件名是否已存在，避免覆盖
                if os.path.exists(new_path):
                    print(f"[跳过] 目标文件已存在: {new_filename} (原文件: {filename})")
                    continue

                if dry_run:
                    print(f"[计划重命名] '{filename}' -> '{new_filename}'")
                else:
                    try:
                        os.rename(old_path, new_path)
                        print(f"[成功] '{filename}' -> '{new_filename}'")
                        renamed_count += 1
                    except Exception as e:
                        print(f"[失败] 无法重命名 '{filename}': {e}")

    if not dry_run:
        print("-" * 50)
        print(f"完成! 共重命名 {renamed_count} 个文件。")
    else:
        print("-" * 50)
        print("以上是模拟运行结果。如需实际执行，请添加 --execute 参数。")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='批量移除 Obsidian 笔记(.md)文件名中的 YYYYMMDD- 前缀')
    parser.add_argument('directory', help='需要处理的根目录路径')
    parser.add_argument('--execute', action='store_true', help='实际执行重命名操作（默认仅为模拟运行）')

    args = parser.parse_args()

    # 默认 dry_run=True，确保用户先预览效果
    rename_files_in_directory(args.directory, dry_run=not args.execute)
