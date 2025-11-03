#!/usr/bin/env python3
"""
下载 jina-embeddings-v3 模型的依赖模块
在有网络连接的机器上运行此脚本，下载所需的依赖文件
"""
import os
from transformers import AutoConfig

def download_dependencies():
    """下载 jina-embeddings-v3 需要的依赖模块"""
    print("正在下载 jina-embeddings-v3 模型的依赖模块...")
    print("这可能需要一些时间，请耐心等待...\n")
    
    try:
        # 尝试加载配置，这会触发依赖下载
        config = AutoConfig.from_pretrained(
            "jinaai/jina-embeddings-v3",
            trust_remote_code=True,
        )
        print("✅ 依赖模块下载成功！")
        print(f"配置已加载: {config._name_or_path}")
        return True
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        print("\n请确保：")
        print("1. 网络连接正常")
        print("2. 可以访问 huggingface.co")
        print("3. 有足够的磁盘空间")
        return False

if __name__ == "__main__":
    success = download_dependencies()
    if success:
        print("\n现在您可以在离线环境下运行应用了。")
    else:
        print("\n请检查网络连接后重试。")

