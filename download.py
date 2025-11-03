from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="jinaai/jina-embeddings-v3",
    local_dir="assets/model",
    local_dir_use_symlinks=False,  # 避免软链接，直接下载文件
    resume_download=True,          # 支持断点续传
    token=None                     # 公开模型无需 token
)