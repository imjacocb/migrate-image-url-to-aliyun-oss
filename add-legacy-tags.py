import os
import sys
import re
import yaml
import argparse

def process_markdown_files(target_dir, dry_run=True):
    """
    遍历 target_dir 下的所有 .md 文件，添加 legacy tags。
    标签路径基于【当前工作目录】计算，以保留完整的文件夹层级。
    并将路径中的 '.', ' ', '_', '&' 替换为 '-'。
    """
    # 规范化目标目录路径
    target_dir = os.path.abspath(target_dir)

    # 获取当前工作目录作为路径计算的基准 (Base Dir)
    base_dir = os.getcwd()

    if not os.path.exists(target_dir):
        print(f"错误: 目标目录不存在 - {target_dir}")
        return

    mode_str = "【模拟运行/干跑】" if dry_run else "【实际执行】"
    print(f"{mode_str} 开始扫描目录: {target_dir}")
    print(f"          路径基准 (CWD): {base_dir}")

    modified_count = 0
    skipped_count = 0

    # 遍历目标目录下的所有文件
    for dirpath, dirnames, filenames in os.walk(target_dir):
        for filename in filenames:
            if not filename.endswith('.md'):
                continue

            filepath = os.path.join(dirpath, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 1. 检查是否有 YAML Front Matter
                fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

                has_fm = bool(fm_match)
                fm_content = ""
                fm_data = {}

                if has_fm:
                    fm_content = fm_match.group(1)
                    # 2. 解析 YAML
                    try:
                        fm_data = yaml.safe_load(fm_content)
                        if not isinstance(fm_data, dict):
                            fm_data = {}
                    except yaml.YAMLError:
                        print(f"警告: YAML 解析失败，跳过文件 - {filepath}")
                        continue

                    # 3. 判断是否为老笔记 (存在 created 或 notedate)
                    is_legacy = 'created' in fm_data or 'notedate' in fm_data
                    if not is_legacy:
                        # 有 FM 但不是老笔记，跳过
                        continue
                else:
                    # 没有 Front Matter，我们将为其创建一个新的
                    pass

                # 4. 计算 relative directory path (基于当前工作目录 base_dir)
                try:
                    rel_path = os.path.relpath(filepath, base_dir)
                except ValueError:
                    print(f"警告: 无法计算相对路径 (可能跨驱动器) - {filepath}")
                    continue

                dir_path = os.path.dirname(rel_path)

                # 构建 tag 值
                if dir_path == '.' or dir_path == '':
                    tag_value = "legacy"
                else:
                    # 关键修改：格式化路径
                    # 1. 将 Windows 分隔符 \ 替换为 /
                    formatted_path = dir_path.replace(os.sep, '/')
                    # 2. 将 . 替换为 -
                    formatted_path = formatted_path.replace('.', '-')
                    # 3. 将 空格 替换为 -
                    formatted_path = formatted_path.replace(' ', '-')
                    # 4. 将 _ 替换为 -
                    formatted_path = formatted_path.replace('_', '-')
                    # 5. 将 & 替换为 -
                    formatted_path = formatted_path.replace('&', '-')

                    tag_value = f"legacy/{formatted_path}"

                # 5. 构建新的 tags 值
                existing_tags = fm_data.get('tags', [])
                if not isinstance(existing_tags, list):
                    existing_tags = [existing_tags] if existing_tags else []

                # 检查是否已经包含该 tag
                if tag_value in existing_tags:
                    skipped_count += 1
                    continue

                new_tags = existing_tags + [tag_value]

                # 辅助函数：格式化标签列表
                def format_tags_list(tags_list):
                    return ", ".join([str(t) for t in tags_list])

                tags_str_items = format_tags_list(new_tags)
                new_tag_line = f"tags: [{tags_str_items}]"

                new_content = ""

                if has_fm:
                    # --- 情况 A: 已有 Front Matter ---
                    lines = fm_content.split('\n')
                    new_fm_content_lines = []
                    tags_found_in_original = False

                    for line in lines:
                        if line.strip().startswith('tags:'):
                            new_fm_content_lines.append(new_tag_line)
                            tags_found_in_original = True
                        else:
                            new_fm_content_lines.append(line)

                    if not tags_found_in_original:
                        new_fm_content_lines.append(new_tag_line)

                    new_fm_content = "\n".join(new_fm_content_lines)
                    start_idx = fm_match.start()
                    end_idx = fm_match.end()
                    new_fm_block = f"---\n{new_fm_content}\n---\n"
                    new_content = content[:start_idx] + new_fm_block + content[end_idx:]

                else:
                    # --- 情况 B: 没有 Front Matter ---
                    # 创建一个新的 Front Matter 块
                    new_fm_block = f"---\n{new_tag_line}\n---\n\n"
                    # 拼接到文件头部
                    new_content = new_fm_block + content

                # 7. 写入文件或仅打印
                if dry_run:
                    print(f"[Dry Run] 将处理: {filepath}")
                    print(f"          -> 添加标签: {tag_value}")
                    if not has_fm:
                        print(f"          -> 动作: 创建新的 Front Matter")
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"[Success] 已修改: {filepath}")
                    print(f"          -> 添加标签: {tag_value}")
                    if not has_fm:
                        print(f"          -> 动作: 创建新的 Front Matter")

                modified_count += 1

            except Exception as e:
                print(f"处理文件时发生错误 {filepath}: {e}")

    print(f"\n处理完成。")
    print(f"成功处理/将处理: {modified_count} 个文件")
    print(f"跳过(标签已存在或非目标文件): {skipped_count} 个文件")
    if dry_run:
        print("\n注意: 当前为模拟运行，文件未被修改。")
        print("如需实际修改，请添加 --no-dry-run 参数。")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='为旧笔记添加 legacy 标签')
    parser.add_argument('directory', help='要处理的笔记目录')
    parser.add_argument('--no-dry-run', '-e', action='store_true',
                        help='实际执行文件修改 (默认仅为模拟运行)')

    args = parser.parse_args()

    is_dry_run = not args.no_dry_run

    process_markdown_files(args.directory, dry_run=is_dry_run)
