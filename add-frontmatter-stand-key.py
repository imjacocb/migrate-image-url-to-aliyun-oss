import os
import re
import sys

def extract_date_lines(content):
    """
    从内容中提取包含 '创建时间:' 和 '更新时间:' 的完整行
    返回一个列表，包含找到的行字符串
    """
    lines = content.splitlines()
    found_lines = []

    for line in lines:
        # 检查行是否以 '创建时间:' 或 '更新时间:' 开头 (忽略前导空格)
        stripped = line.strip()
        if stripped.startswith('创建时间:') or stripped.startswith('更新时间:'):
            found_lines.append(line)

    return found_lines

def has_existing_frontmatter(content):
    """
    检查文件是否已经以 YAML Frontmatter 开头 (以 --- 开始)
    """
    stripped_content = content.lstrip()
    return stripped_content.startswith('---')

def process_file(file_path):
    """
    处理单个 markdown 文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return False

    # 1. 如果已经有 Frontmatter，跳过
    if has_existing_frontmatter(content):
        # print(f"Skipped (has frontmatter): {file_path}")
        return False

    # 2. 提取特定的时间行
    date_lines = extract_date_lines(content)

    # 如果没有找到任何时间行，则不需要处理
    if not date_lines:
        return False

    # 3. 构建 YAML Frontmatter
    yaml_header = "---\n"
    for line in date_lines:
        # 核心修改：在这里进行键名替换
        processed_line = line
        if '创建时间:' in processed_line:
            processed_line = processed_line.replace('创建时间:', 'created:', 1)
        elif '更新时间:' in processed_line:
            processed_line = processed_line.replace('更新时间:', 'modified:', 1)

        yaml_header += f"{processed_line}\n"

    yaml_header += "---\n\n" # 结尾加两个换行，确保与正文分隔

    # 4. 从原文中移除这两行 (避免正文中重复出现)
    # 重构内容，跳过那些被提取到 frontmatter 的行
    original_lines = content.splitlines(keepends=True)

    # 准备一个用于比较的集合，存储原始行的 stripped 版本
    # 注意：我们移除的是原始文件中包含中文键名的行
    lines_to_remove_stripped = set([l.strip() for l in date_lines])

    final_body_lines = []
    for line in original_lines:
        if line.strip() in lines_to_remove_stripped:
            continue # 跳过这一行，因为它已经在 frontmatter 里了（且已转换为英文键名）
        else:
            final_body_lines.append(line)

    new_content_body = "".join(final_body_lines)

    # 5. 组合新内容
    new_content = yaml_header + new_content_body

    # 6. 写回文件
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {file_path}")
        return True
    except Exception as e:
        print(f"Error writing file {file_path}: {e}")
        return False

def main(directory):
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        sys.exit(1)

    processed_count = 0

    # 遍历目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                if process_file(file_path):
                    processed_count += 1

    print(f"\nDone. Processed {processed_count} files.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_frontmatter_standard_keys.py <directory_path>")
        sys.exit(1)

    target_dir = sys.argv[1]
    main(target_dir)
