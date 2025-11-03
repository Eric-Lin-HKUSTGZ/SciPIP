import requests
import json

class LLMClient:
    def __init__(self, api_key, base_url, model_name):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def chat(self, messages, temperature=0.7, max_tokens=2000, stream=False):
        """
        聊天补全接口
        """
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=data,
                timeout=60,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                result = response.json()
                return result['choices'][0]['message']['content']
                
        except Exception as e:
            print(f"API调用失败: {e}")
            return None
    
    def _handle_stream_response(self, response):
        """
        处理流式响应
        """
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        json_data = json.loads(data)
                        if 'choices' in json_data and len(json_data['choices']) > 0:
                            delta = json_data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                print(content, end='', flush=True)
                                full_response += content
                    except json.JSONDecodeError:
                        continue
        print()  # 换行
        return full_response
    
    def get_models(self):
        """
        获取可用的模型列表
        """
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return None

# 使用示例
client = LLMClient(
    api_key="sk-OUklCXtmOyGEpre35ls9QFp3xKDlFB3VTLEOgFJlQVAkMhzd",
    base_url="http://35.220.164.252:3888",
    model_name="gpt-5"
)

# 测试连接
models = client.get_models()
if models:
    print("可用模型:", [model['id'] for model in models.get('data', [])])

# 聊天对话
messages = [
    {"role": "system", "content": "你是一个专业的AI助手。"},
    {"role": "user", "content": "请帮我写一个Python函数来计算斐波那契数列。"}
]

response = client.chat(messages)
print("助手回复:", response)