import os
import sys
import xml.etree.ElementTree as ET
import re
from datetime import datetime

def parse_note_file(file_path):
    """
    解析 .note 文件，提取日期、标题和链接内容
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # 定义命名空间，Youdao Note 通常有 xmlns
        ns = {'ns': 'http://note.youdao.com'}

        # 提取链接文本
        # 尝试查找 //text 节点
        text_elements = root.findall('.//ns:text', ns)
        link_content = ""
        if text_elements:
            # 取第一个 text 节点的内容
            link_content = text_elements[0].text.strip() if text_elements[0].text else ""

        return link_content
    except Exception as e:
        print(f"解析文件 {file_path} 出错: {e}")
        return None

def convert_date_format(date_str):
    """
    将 YYYYMMDD 转换为 YYYY-MM-DD
    """
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def process_notes(directory):
    """
    处理目录下所有的 .note 文件
    """
    if not os.path.isdir(directory):
        print(f"错误: 路径 '{directory}' 不是一个有效的目录。")
        return

    # 遍历目录
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if not filename.endswith('.note'):
                continue

            file_path = os.path.join(root, filename)

            # 1. 解析文件名提取日期和标题
            # 假设格式为: YYYYMMDD-Title.note
            match = re.match(r'^(\d{8})-(.+)\.note$', filename)
            if not match:
                print(f"跳过不符合命名规范的文件: {filename}")
                continue

            date_str_raw = match.group(1)
            title_part = match.group(2)

            # 转换日期格式
            notedate = convert_date_format(date_str_raw)
            if not notedate:
                print(f"跳过日期格式错误的文件: {filename}")
                continue

            # 2. 解析文件内容提取链接
            link_url = parse_note_file(file_path)
            if link_url is None:
                # 如果解析失败，可以选择跳过或保留空值，这里选择跳过
                continue

            # 3. 构建新的文件名 (去掉时间戳)
            new_filename = f"{title_part}.md"
            new_file_path = os.path.join(root, new_filename)

            # 检查目标文件是否已存在，避免覆盖
            if os.path.exists(new_file_path):
                print(f"警告: 文件已存在，跳过: {new_file_path}")
                continue

            # 4. 构建 Markdown 内容
            # YAML Front Matter (去掉了引号)
            yaml_front_matter = f"""---
notedate: {notedate}
from: {link_url}
---

"""
            # 正文内容 (可选：将链接也放入正文，方便点击)
            body_content = f"[原始链接]({link_url})\n"

            final_content = yaml_front_matter + body_content

            # 5. 写入新文件
            try:
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)

                # 6. 删除原 .note 文件
                os.remove(file_path)
                print(f"成功转换并删除: {filename} -> {new_filename}")

            except Exception as e:
                print(f"处理文件 {filename} 失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python convert_old_notes.py <folder_path>")
        sys.exit(1)

    target_folder = sys.argv[1]
    process_notes(target_folder)
