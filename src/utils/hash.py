import re
import os
import hashlib
import torch
import struct
from collections import Counter
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer
from .header import get_dir

ENV_CHECKED = False
EMBEDDING_CHECKED = False


def check_embedding(repo_id):
    print("=== check embedding model ===")
    global EMBEDDING_CHECKED
    if not EMBEDDING_CHECKED:
        # Define the repository and files to download
        local_dir = f"./assets/model/{repo_id}"
        if repo_id in [
            "sentence-transformers/all-MiniLM-L6-v2",
            "BAAI/bge-small-en-v1.5",
            "BAAI/llm-embedder",
        ]:
            # repo_id = "sentence-transformers/all-MiniLM-L6-v2"
            # repo_id = "BAAI/bge-small-en-v1.5"
            files_to_download = [
                "config.json",
                "pytorch_model.bin",
                "tokenizer_config.json",
                "vocab.txt",
            ]
        elif repo_id in [
            "jinaai/jina-embeddings-v3",
        ]:
            files_to_download = [
                "model.safetensors",
                "modules.json",
                "tokenizer.json",
                "config_sentence_transformers.json",
                "custom_st.py",
                "special_tokens_map.json",
                "tokenizer_config.json",
                "1_Pooling/config.json",
                "config.json",
            ]
        elif repo_id in ["Alibaba-NLP/gte-base-en-v1.5"]:
            files_to_download = [
                "config.json",
                "model.safetensors",
                "modules.json",
                "tokenizer.json",
                "sentence_bert_config.json",
                "tokenizer_config.json",
                "vocab.txt",
            ]
        # Download each file and save it to the /model/bge directory
        for file_name in files_to_download:
            if not os.path.exists(os.path.join(local_dir, file_name)):
                print(
                    f"file: {file_name} not exist in {local_dir}, try to download from huggingface ..."
                )
                hf_hub_download(
                    repo_id=repo_id,
                    filename=file_name,
                    local_dir=local_dir,
                )
        EMBEDDING_CHECKED = True


def check_env():
    global ENV_CHECKED
    if not ENV_CHECKED:
        env_name_list = [
            "NEO4J_URL",
            "NEO4J_USERNAME",
            "NEO4J_PASSWD",
            "MODEL_NAME",
            "MODEL_TYPE",
            "BASE_URL",
        ]
        for env_name in env_name_list:
            if env_name not in os.environ or os.environ[env_name] == "":
                raise ValueError(f"{env_name} is not set...")
        if os.environ["MODEL_TYPE"] != "Local":
            env_name = "MODEL_API_KEY"
            if env_name not in os.environ or os.environ[env_name] == "":
                raise ValueError(f"{env_name} is not set...")
        ENV_CHECKED = True


class EmbeddingModel:
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            local_dir = f"./assets/model/{config.DEFAULT.embedding}"
            cls._instance = super(EmbeddingModel, cls).__new__(cls)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 保存原始环境变量
            original_offline = os.environ.get("TRANSFORMERS_OFFLINE", "0")
            original_hf_offline = os.environ.get("HF_HUB_OFFLINE", "0")
            
            # 获取本地模型路径
            model_path = get_dir(local_dir)
            
            try:
                # 检查是否是 jina-embeddings-v3，需要特殊处理
                if "jina-embeddings-v3" in config.DEFAULT.embedding:
                    # 强制使用离线模式，完全使用本地文件
                    # 设置环境变量强制离线
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    os.environ["HF_DATASETS_OFFLINE"] = "1"
                    
                    print(f"正在从本地路径加载模型: {model_path}")
                    print("使用离线模式，不会尝试网络连接...")
                    
                    # 检查模型目录是否存在
                    if not os.path.exists(model_path):
                        raise FileNotFoundError(
                            f"模型目录不存在: {model_path}\n"
                            f"请确保模型已下载到指定位置。"
                        )
                    
                    # 直接使用 local_files_only=True，强制只使用本地文件
                    # 注意：可能会看到权重不匹配警告，这是正常的
                    # jina-embeddings-v3 使用自定义架构（LoRA），但在离线模式下
                    # SentenceTransformer 仍能正确加载和使用模型
                    import warnings
                    import logging
                    # 设置 transformers 日志级别，减少警告输出
                    transformers_logger = logging.getLogger("transformers.modeling_utils")
                    original_level = transformers_logger.level
                    transformers_logger.setLevel(logging.ERROR)
                    
                    try:
                        with warnings.catch_warnings():
                            # 临时抑制 transformers 的权重警告
                            warnings.filterwarnings("ignore", message=".*not used when initializing.*")
                            warnings.filterwarnings("ignore", message=".*not initialized from.*")
                            warnings.filterwarnings("ignore", message=".*Some weights.*")
                            
                            cls._instance.embedding_model = SentenceTransformer(
                                model_name_or_path=model_path,
                                device=device,
                                trust_remote_code=True,
                                local_files_only=True,  # 强制只使用本地文件
                            )
                    except Exception as e:
                        error_msg = str(e)
                        if "not found" in error_msg.lower() or "local cache" in error_msg.lower():
                            raise RuntimeError(
                                f"无法从本地加载模型。\n"
                                f"模型路径: {model_path}\n"
                                f"错误: {error_msg}\n\n"
                                f"解决方案：\n"
                                f"1. 确保模型文件完整存在于: {model_path}\n"
                                f"2. 检查模型依赖是否已下载到本地缓存\n"
                                f"3. 如果模型文件不完整，请重新下载模型"
                            ) from e
                        else:
                            raise RuntimeError(
                                f"加载本地模型时出错: {error_msg}\n"
                                f"模型路径: {model_path}"
                            ) from e
                    finally:
                        # 恢复日志级别
                        transformers_logger.setLevel(original_level)
                else:
                    # 其他模型使用 local_files_only
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    cls._instance.embedding_model = SentenceTransformer(
                        model_name_or_path=model_path,
                        device=device,
                        trust_remote_code=True,
                        local_files_only=True,
                    )
                
                # 设置 jina-embeddings-v3 的默认任务
                if "jina-embeddings-v3" in config.DEFAULT.embedding:
                    cls._instance.embedding_model[0].default_task = config.DEFAULT.embedding_task
                print(f"==== using device {device} ====")
            finally:
                # 恢复原始环境变量
                os.environ["TRANSFORMERS_OFFLINE"] = original_offline
                os.environ["HF_HUB_OFFLINE"] = original_hf_offline
        return cls._instance


def get_embedding_model(config):
    print("=== get embedding model ===")
    check_embedding(config.DEFAULT.embedding)
    return EmbeddingModel(config).embedding_model


def generate_hash_id(input_string):
    if input_string is None:
        return None
    sha1_hash = hashlib.sha256(input_string.lower().encode("utf-8")).hexdigest()
    binary_hash = bytes.fromhex(sha1_hash)
    int64_hash = struct.unpack(">q", binary_hash[:8])[0]
    return abs(int64_hash)


def extract_ref_id(text, references):
    """
    references: paper["references"]
    """
    # 正则表达式模式，用于匹配[数字, 数字]格式
    pattern = r"\[\d+(?:,\s*\d+)*\]"
    # 提取所有匹配的内容
    ref_list = re.findall(pattern, text)
    # ref ['[15, 16]', '[5]', '[2, 3, 8]']
    combined_ref_list = []
    if len(ref_list) > 0:
        # 说明是pattern 0
        for ref in ref_list:
            # 移除方括号并分割数字
            numbers = re.findall(r"\d+", ref)
            # 将字符串数字转换为整数并加入到列表中
            combined_ref_list.extend(map(int, numbers))
        # 去重并排序
        ref_counts = Counter(combined_ref_list)
        ref_counts = dict(sorted(ref_counts.items()))
        # 对多个，只保留引用最多的一个
        for ref in ref_list:
            # 移除方括号并分割数字
            numbers = re.findall(r"\d+", ref)
            # 找到只引用了一次的
            temp_list = []
            for num in numbers:
                num = int(num)
                if ref_counts[num] == 1:
                    temp_list.append(num)
            if len(temp_list) == len(numbers):
                temp_list = temp_list[1:]
            for num in temp_list:
                del ref_counts[num]
    hash_id_list = []
    for idx in ref_counts.keys():
        hash_id_list.append(generate_hash_id(references[idx]))
    return hash_id_list


if __name__ == "__main__":
    # 示例用法
    input_string = "example_string"
    hash_id = generate_hash_id(input_string)
    print("INT64 Hash ID:", hash_id)
