import os
import re
import sys
import logging
import oss2
from urllib.parse import quote, unquote

# ================= 配置区域 =================
# 请替换为你的真实配置
OSS_CONFIG = {
    'endpoint': 'oss-cn-shanghai.aliyuncs.com',  # 你的OSS Endpoint
    'access_key_id': '',        # 你的AccessKey ID
    'access_key_secret': '',# 你的AccessKey Secret
    'bucket_name': '',            # 你的Bucket名称
    'folder_prefix': 'youdao-note-images-full/',                # OSS中的文件夹前缀，末尾带/
    'cdn_domain': ''                              # 如果绑定了CDN，填写CDN域名，否则留空使用OSS默认域名
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= 核心逻辑类 =================
class OssImageReplacer:
    def __init__(self, config):
        self.config = config
        # 初始化 OSS Auth 和 Bucket
        auth = oss2.Auth(config['access_key_id'], config['access_key_secret'])
        self.bucket = oss2.Bucket(auth, config['endpoint'], config['bucket_name'])
        
        # 匹配 Markdown 图片语法: ![alt](path) 或 <img src="path" />
        # 这里主要处理标准的 ![alt](path) 格式
        self.md_image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def is_local_image(self, path):
        """判断路径是否为本地相对路径图片"""
        if not path:
            return False
        # 排除网络图片 (http://, https://, data:image)
        if path.startswith(('http://', 'https://', 'data:')):
            return False
        # 排除绝对路径（视需求而定，通常只处理相对路径）
        if os.path.isabs(path):
            return False
        return True

    def upload_to_oss(self, local_file_path, oss_object_name):
        """上传文件到 OSS"""
        try:
            # 检查文件是否存在
            if not os.path.exists(local_file_path):
                logger.warning(f"文件不存在，跳过: {local_file_path}")
                return None
            
            # 上传文件
            with open(local_file_path, 'rb') as fileobj:
                self.bucket.put_object(oss_object_name, fileobj)
            
            # 构建 URL
            if self.config['cdn_domain']:
                url = f"https://{self.config['cdn_domain']}/{oss_object_name}"
            else:
                # 使用 OSS 默认域名
                url = f"https://{self.config['bucket_name']}.{self.config['endpoint'].replace('https://', '').replace('http://', '')}/{oss_object_name}"
            
            logger.info(f"上传成功: {local_file_path} -> {url}")
            return url
        except Exception as e:
            logger.error(f"上传失败: {local_file_path}, 错误: {str(e)}")
            return None

    def process_markdown_file(self, md_file_path):
        """处理单个 Markdown 文件"""
        dir_path = os.path.dirname(md_file_path)
        
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {md_file_path}, 错误: {str(e)}")
            return

        matches = list(self.md_image_pattern.finditer(content))
        if not matches:
            logger.info(f"文件中未发现图片链接: {md_file_path}")
            return

        new_content = content
        # 逆序替换，避免索引偏移问题
        for match in reversed(matches):
            alt_text = match.group(1)
            image_path = match.group(2).strip()
            
            # 清理可能存在的标题部分 "image.png#width=100"
            clean_image_path = image_path.split('#')[0]

            if not self.is_local_image(clean_image_path):
                continue

            # 构建本地文件的绝对路径
            local_image_full_path = os.path.normpath(os.path.join(dir_path, clean_image_path))
            

             # 对路径进行 URL 解码，将 %20 等转换回空格
            # 例如: "屏幕截图%202025.png" -> "屏幕截图 2025.png"
            try:
                decoded_image_path = unquote(clean_image_path)
            except Exception:
                decoded_image_path = clean_image_path
            
            # 构建本地文件的绝对路径 (使用解码后的路径)
            local_image_full_path = os.path.normpath(os.path.join(dir_path, decoded_image_path))


            # 检查文件是否真的存在
            if not os.path.exists(local_image_full_path):
                logger.warning(f"图片文件未找到，跳过替换: {local_image_full_path}")
                continue


            # 检查文件大小，仅处理大于 100KB 的图片
            # try:
            #     file_size = os.path.getsize(local_image_full_path)
            #     size_limit = 50 * 1024  # 100 KB
            #     if file_size <= size_limit:
            #         logger.info(f"图片小于 100KB ({file_size} bytes)，跳过处理: {local_image_full_path}")
            #         continue
            # except Exception as e:
            #     logger.warning(f"获取文件大小失败，跳过处理: {local_image_full_path}, 错误: {str(e)}")
            #     continue

            # 生成 OSS 对象名称 (保持原有文件名，或者使用哈希防止重名)
            # 这里简单使用原文件名，建议加上随机前缀或哈希以避免冲突
            file_name = os.path.basename(decoded_image_path)
            # 可选：使用文件内容的 MD5 作为文件名以防重复
            # import hashlib
            # with open(local_image_full_path, 'rb') as f:
            #     file_hash = hashlib.md5(f.read()).hexdigest()
            # ext = os.path.splitext(file_name)[1]
            # oss_object_name = f"{self.config['folder_prefix']}{file_hash}{ext}"
            

            # 可选：为了 OSS 兼容性，可以将文件名中的空格替换为下划线
            safe_file_name = file_name.replace(' ', '_')
            oss_object_name = f"{self.config['folder_prefix']}{safe_file_name}"
            
            # 上传
            oss_url = self.upload_to_oss(local_image_full_path, oss_object_name)
            
            if oss_url:
                # 替换 Markdown 中的链接
                # 注意：需要转义特殊字符以符合 Regex 替换要求，但这里直接替换整个匹配串更简单
                original_markdown_img = match.group(0)
                new_markdown_img = f"![{alt_text}]({oss_url})"
                
                # 由于我们是逆序遍历，直接替换字符串是安全的
                new_content = new_content.replace(original_markdown_img, new_markdown_img, 1)
                
                # 删除本地图片
                try:
                    os.remove(local_image_full_path)
                    logger.info(f"已删除本地图片: {local_image_full_path}")

                    # ================= 检查并删除空目录 =================
                    parent_dir = os.path.dirname(local_image_full_path)
                    # 确保父目录存在且不为根目录或当前工作目录等敏感位置（可选保护）
                    if parent_dir and os.path.exists(parent_dir):
                        # 检查目录是否为空
                        if not os.listdir(parent_dir):
                            try:
                                os.rmdir(parent_dir)
                                logger.info(f"目录已空，已删除目录: {parent_dir}")
                            except Exception as e:
                                logger.warning(f"删除空目录失败: {parent_dir}, 错误: {str(e)}")
                    # ==========================================================

                except Exception as e:
                    logger.error(f"删除本地图片失败: {local_image_full_path}, 错误: {str(e)}")
            else:
                logger.warning(f"因上传失败，保留原链接: {image_path}")

        # 写入新内容
        if new_content != content:
            try:
                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"文件更新完成: {md_file_path}")
            except Exception as e:
                logger.error(f"写入文件失败: {md_file_path}, 错误: {str(e)}")

    def scan_and_process_directory(self, root_dir):
        """遍历目录处理所有 .md 文件"""
        for root, dirs, files in os.walk(root_dir):
            # 忽略隐藏文件夹和 node_modules 等常见无关目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '.git']]
            
            for file in files:
                if file.lower().endswith('.md'):
                    md_path = os.path.join(root, file)
                    logger.info(f"正在处理: {md_path}")
                    self.process_markdown_file(md_path)

# ================= 主程序入口 =================
if __name__ == '__main__':
    # 1. 检查配置
    if 'YOUR_ACCESS_KEY' in OSS_CONFIG['access_key_id']:
        print("错误: 请先在代码中配置正确的 OSS AccessKey 和 Bucket 信息。")
        sys.exit(1)

    # 2. 指定要处理的根目录 (默认为当前脚本所在目录，也可手动指定)
    TARGET_DIRECTORY = '.' 
    if len(sys.argv) > 1:
        TARGET_DIRECTORY = sys.argv[1]

    if not os.path.isdir(TARGET_DIRECTORY):
        print(f"错误: 目录不存在: {TARGET_DIRECTORY}")
        sys.exit(1)

    print(f"开始处理目录: {os.path.abspath(TARGET_DIRECTORY)}")
    
    # 3. 执行
    replacer = OssImageReplacer(OSS_CONFIG)
    replacer.scan_and_process_directory(TARGET_DIRECTORY)
    
    print("处理完成。")
