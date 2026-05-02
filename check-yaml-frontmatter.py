import os
import sys
import re
import yaml
import argparse

def check_yaml_frontmatter(filepath):
    """
    检查单个文件的 YAML Front Matter 是否合法
    返回: (True, data) 如果合法, (False, error_msg) 如果非法
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 Front Matter
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

        if not fm_match:
            return True, None # 没有 FM 也算“通过”检查，或者你可以选择返回 False

        fm_content = fm_match.group(1)

        # 尝试解析 YAML
        data = yaml.safe_load(fm_content)

        # 确保解析结果是字典（标准的 FM 应该是键值对）
        if not isinstance(data, dict):
            return False, "Front Matter 解析结果不是字典 (可能是列表或标量)"

        return True, data

    except yaml.YAMLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='检查 Markdown 文件的 YAML Front Matter 语法')
    parser.add_argument('directory', help='要检查的目录')
    args = parser.parse_args()

    root_dir = os.path.abspath(args.directory)
    error_count = 0
    checked_count = 0

    print(f"开始检查目录: {root_dir}\n")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith('.md'):
                continue

            filepath = os.path.join(dirpath, filename)
            is_valid, msg = check_yaml_frontmatter(filepath)
            checked_count += 1

            if not is_valid:
                error_count += 1
                # 打印相对路径以便定位
                rel_path = os.path.relpath(filepath, root_dir)
                print(f"[ERROR] {rel_path}")
                print(f"        原因: {msg}\n")

    print(f"检查完成。共检查 {checked_count} 个文件，发现 {error_count} 个错误。")

if __name__ == '__main__':
    main()
