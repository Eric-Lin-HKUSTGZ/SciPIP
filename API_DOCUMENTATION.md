# SciPIP API 文档

## 概述

SciPIP API 是一个基于 FastAPI 的 RESTful API 服务，用于生成科学论文研究想法。该 API 封装了 SciPIP 的核心功能，支持流式和非流式响应。

## 快速开始

### 启动服务

**开发模式（前台运行）:**
```bash
# 方式1: 使用启动脚本
python start_api.py

# 方式2: 直接运行
python api_service.py

# 方式3: 使用 uvicorn
uvicorn api_service:app --host 0.0.0.0 --port 8888
```

**生产模式（后台运行）:**
```bash
# 启动服务（后台运行）
sh start_prod.sh start

# 查看服务状态
sh start_prod.sh status

# 查看日志
sh start_prod.sh logs

# 停止服务
sh start_prod.sh stop

# 重启服务
sh start_prod.sh restart
```

### 检查服务状态

```bash
curl http://localhost:8888/health
```

## API 端点

### 1. 健康检查

**GET** `/health`

检查 API 服务是否正常运行。

**响应示例:**
```json
{
  "status": "healthy",
  "service": "SciPIP API",
  "version": "1.0.0",
  "backend_ready": true
}
```

### 2. 生成研究想法

**POST** `/generate`

生成科学论文研究想法（一键生成模式）。

**请求体:**
```json
{
  "background": "你的研究背景信息...",
  "stream": false
}
```

**参数说明:**
- `background` (必需): 研究背景信息，字符串，至少1个字符
- `stream` (可选): 是否使用流式响应，默认为 `false`

**响应 (非流式):**
```json
{
  "status": "success",
  "entities_bg": ["entity1", "entity2"],
  "expanded_background": "扩展后的背景信息...",
  "brainstorms": "头脑风暴结果...",
  "entities_all": ["entity1", "entity2", "entity3"],
  "related_works": ["Paper 1. VENUE 2024.", "Paper 2. VENUE 2023."],
  "related_works_count": 10,
  "initial_ideas_count": 5,
  "final_ideas_count": 5,
  "ideas": [
    {
      "index": 1,
      "concise_idea": "简洁的想法描述...",
      "idea_in_detail": "详细的想法描述..."
    },
    ...
  ]
}
```

**响应 (流式):**

流式响应使用 Server-Sent Events (SSE) 格式，每行以 `data: ` 开头，后跟 JSON 数据。

消息类型包括:
- `query_received`: 查询已接收
- `step_start`: 步骤开始
- `step_complete`: 步骤完成
- `final_result`: 最终结果
- `error`: 错误信息

**示例:**
```
data: {"type": "query_received", "data": {"background": "..."}}

data: {"type": "step_start", "data": {"step": "extract_entities", "message": "Extracting entities..."}}

data: {"type": "step_complete", "data": {"step": "extract_entities", "entities": [...], "message": "Successfully extracted 5 entities"}}

...

data: {"type": "final_result", "data": {"initial_ideas_count": 5, "final_ideas_count": 5, "ideas": [...]}}
```

## 使用示例

### Python 客户端

```python
import asyncio
from python_client_example import SciPIPClient, MessageHandler

async def main():
    client = SciPIPClient()
    handler = MessageHandler()
    
    # 检查服务状态
    health = await client.check_health()
    print(f"Service status: {health['status']}")
    
    # 生成想法（流式）
    background = "你的研究背景..."
    result = await client.generate_ideas_stream(
        background, 
        on_message=handler.handle_message
    )
    
    # 或使用同步方式
    result = await client.generate_ideas_sync(background)

asyncio.run(main())
```

### cURL 示例

```bash
# 非流式生成
curl -X POST http://localhost:8888/generate \
  -H "Content-Type: application/json" \
  -d '{
    "background": "I am interested in improving the interpretability of deep learning models.",
    "stream": false
  }'

# 流式生成
curl -X POST http://localhost:8888/generate \
  -H "Content-Type: application/json" \
  -d '{
    "background": "I am interested in improving the interpretability of deep learning models.",
    "stream": true
  }'
```

### JavaScript/Node.js 示例

```javascript
const fetch = require('node-fetch');

async function generateIdeas(background) {
  const response = await fetch('http://localhost:8888/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      background: background,
      stream: false
    })
  });
  
  const result = await response.json();
  console.log(result);
}
```

## 配置

### 环境变量

API 服务支持以下环境变量配置（也可在 `api_config.py` 中直接修改）:

- `SCIPIP_API_HOST`: API 服务主机地址，默认 `0.0.0.0`
- `SCIPIP_API_PORT`: API 服务端口，默认 `8888`
- `SCIPIP_LOG_LEVEL`: 日志级别，默认 `INFO`
- `SCIPIP_ALLOWED_ORIGINS`: CORS 允许的源，用逗号分隔，默认 `*`

### 配置文件

API 服务会自动从 `scripts/env.sh` 加载 SciPIP 所需的环境变量（如 `MODEL_NAME`, `NEO4J_URL` 等）。

## 错误处理

API 使用标准 HTTP 状态码:

- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误
- `501`: 功能未实现

错误响应格式:
```json
{
  "detail": "错误描述信息"
}
```

## 性能注意事项

- 生成想法可能需要较长时间（最多 5 分钟），建议使用流式响应以获取实时进度
- 如果 API 调用超时，请检查网络连接和 API 服务器状态
- 某些步骤（如文献检索）可能需要访问 Neo4j 数据库，请确保数据库正常运行

## 依赖项

主要依赖:
- `fastapi`: Web 框架
- `uvicorn`: ASGI 服务器
- `pydantic`: 数据验证
- `aiohttp`: 异步 HTTP 客户端（客户端示例）

安装依赖:
```bash
pip install fastapi uvicorn pydantic aiohttp
```

## 许可证

与 SciPIP 项目保持一致。

