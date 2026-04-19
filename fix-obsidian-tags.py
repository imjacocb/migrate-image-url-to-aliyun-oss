import os
import re
import sys

def should_escape_hash(line_content, hash_index):
    """
    判断当前的 # 是否应该被排除（不转义）
    1. C/C++ 预处理指令
    2. Linux 设备树属性
    3. Markdown 标题 (# Header) - 修复版：处理连续 # 的情况
    4. 单词中间的 # (如 C#, A#B) - Obsidian 不将其识别为标签
    5. 如果 # 后面是空格或行尾，它永远不是标签 

    返回 True: 需要转义
    返回 False: 不需要转义（保留原样）
    """
    
    # 1. 检查 # 后面的字符
    if hash_index + 1 >= len(line_content):
        return False # 行尾，不转义
    
    next_char = line_content[hash_index + 1]
    
    # 【最高优先级】如果 # 后面是任何空白字符，绝对不转义
    # 这涵盖了: 
    # - "# Title" (标题)
    # - "1. # Comment" (列表注释)
    # - "# " (无效标签)
    if next_char.isspace():
        return False 

    # 2. 检查 # 前面的字符
    if hash_index > 0:
        prev_char = line_content[hash_index - 1]
        # 如果前一个字符不是空白字符，说明在单词中间 (如 C#, A#B)
        # Obsidian 不将其识别为标签，保持源码干净，不转义
        if not prev_char.isspace():
            return False 

    # 3. 此时，# 后面是非空白字符，且前面是空白或行首。
    # 这可能是标签 (#Tag)，也可能是误判 (#123, #7f...)。
    # 我们需要排除合法的 C 宏和设备树属性。
    
    suffix = line_content[hash_index+1:].lstrip()
    
    # 排除 C/C++ 宏
    c_macros = [
        'define', 'include', 'ifdef', 'ifndef', 'endif', 'elif', 
        'pragma', 'error', 'warning', 'line', 'undef'
    ]
    for macro in c_macros:
        if suffix.lower().startswith(macro):
            next_char_idx = len(macro)
            if next_char_idx >= len(suffix) or not suffix[next_char_idx].isalnum():
                return False # 是宏，不转义

    # 排除 Linux 设备树属性
    dts_props = [
        'address-cells', 'size-cells', 'interrupt-cells', 
        'gpio-cells', 'phandle', 'clock-cells'
    ]
    for prop in dts_props:
        if suffix.startswith(prop):
             rest = suffix[len(prop):]
             if rest.startswith(':') or rest.isspace() or rest == '':
                 return False # 是 DTS 属性，不转义

    # 4. 【新增强化】二次检查：是否是带缩进的标题？
    # 虽然上面的 "next_char.isspace()" 应该已经覆盖了标准标题，
    # 但为了防止类似 "###NoSpace" 这种极端情况被误伤（虽然它也不是合法标题），
    # 我们这里主要处理的是：如果 # 后面紧跟的是 #，我们需要确保整个序列被正确识别。
    
    # 如果当前 # 后面还是 #，说明它是标题序列的一部分。
    # 由于第一步已经排除了 "# " (后接空格)，那么 "## Title" 中的第一个 # 
    # 其后继字符是 '#' (非空格)，所以会进入到这里。
    # 我们需要手动识别这种连续 # 的情况。
    
    if next_char == '#':
        # 找到这一串 # 的结束位置
        end_index = hash_index
        while end_index < len(line_content) - 1 and line_content[end_index + 1] == '#':
            end_index += 1
        
        count = end_index - hash_index + 1
        
        # 检查这串 # 之前是否全是空格（即位于行首区域）
        prefix = line_content[:hash_index]
        if prefix.strip() == '':
            # 检查 # 序列之后是否是空格或行尾
            next_after_hashes_index = end_index + 1
            if next_after_hashes_index >= len(line_content):
                return False # 例如 "###"
            
            char_after_hashes = line_content[next_after_hashes_index]
            if char_after_hashes.isspace():
                return False # 是标题，例如 "### Title"

    # 5. 剩下的情况：
    # #Tag (正常标签) -> 根据你的要求“这三种之外全加”，这里会转义。
    # #7f0c006f (十六进制) -> 转义。
    # #123 (数字) -> 转义。
    
    # 如果你希望保留正常的 #Tag 不被转义，请取消下面这行的注释：
    # if re.match(r'^[\w\u4e00-\u9fff/]', suffix): return False

    return True # 默认转义

def is_in_code_block(lines, current_line_index):
    fence_count = 0
    for i in range(current_line_index):
        line = lines[i].strip()
        if line.startswith('```') or line.startswith('~~~'):
            fence_count += 1
    return fence_count % 2 != 0

def is_in_yaml_front_matter(lines, current_line_index):
    if current_line_index == 0:
        return False
    if lines[0].strip() != '---':
        return False
    for i in range(1, current_line_index + 1):
        if lines[i].strip() == '---':
            return False
    return True

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    new_lines = []
    modified = False
    
    for i, line in enumerate(lines):
        # 1. YAML Front Matter 跳过
        if is_in_yaml_front_matter(lines, i):
            new_lines.append(line)
            continue
            
        # 2. 代码块跳过
        if is_in_code_block(lines, i):
            new_lines.append(line)
            continue
            
        # 3. 处理行内的 #
        new_line_content = list(line)
        
        # 查找所有未被转义的 #
        matches = list(re.finditer(r'(?<!\\)#', line))
        
        if not matches:
            new_lines.append(line)
            continue
            
        line_modified = False
        # 从后往前处理
        for match in reversed(matches):
            pos = match.start()
            
            # 核心判断：是否应该转义？
            if not should_escape_hash(line, pos):
                continue
                
            # 执行转义
            new_line_content.insert(pos, '\\')
            line_modified = True
            
        if line_modified:
            new_lines.append(''.join(new_line_content))
            modified = True
        else:
            new_lines.append(line)

    if modified:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"Fixed: {filepath}")
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False
    else:
        return False

def main(folder_path):
    folder_path = folder_path.strip().strip('"').strip("'")
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return

    md_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
                
    print(f"Found {len(md_files)} markdown files in '{folder_path}'.")
    fixed_count = 0
    
    for filepath in md_files:
        if process_file(filepath):
            fixed_count += 1
            
    print(f"Done. Fixed {fixed_count} files.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_obsidian_tags.py <folder_path>")
    else:
        folder = sys.argv[1]
        confirm = input(f"Will process all .md files in '{folder}'. MAKE SURE YOU HAVE A BACKUP. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            main(folder)
        else:
            print("Aborted.")
