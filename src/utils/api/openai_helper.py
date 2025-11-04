r"""_summary_
-*- coding: utf-8 -*-

Module : data.utils.api.openai_helper

File Name : openai_helper.py

Description : Helper class for openai interface, generally not used directly.
    For example:
    ```
    from data.utils.api import HelperCompany
    helper = HelperCompany.get()['OpenAI']
    ...
    ```
   
Creation Date : 2024-10-29

Author : Frank Kang(frankkang@zju.edu.cn)
"""
import requests
import json
from .base_helper import register_helper, BaseHelper, NotGiven


@register_helper('OpenAI')
class OpenAIHelper(BaseHelper):
    """_summary_

    Helper class for openai interface, generally not used directly.

    For example:
    ```
    from data.utils.api import HelperCompany
    helper = HelperCompany.get()['OpenAI']
    ...
    ```
    """

    def __init__(self, api_key, model, base_url=None, timeout=None):
        super().__init__(api_key, model, base_url)
        # 增加默认超时时间到 600 秒（10分钟），因为 LLM API 调用可能需要更长时间
        self.timeout = timeout if timeout is not None else 600

    def _build_endpoint(self) -> str:
        base = (self.base_url or "").rstrip('/')
        if base.endswith('/v1'):
            return base + '/chat/completions'
        return base + '/v1/chat/completions'

    def create(
        self,
        *args,
        messages=None,
        stream: bool | NotGiven = None,
        temperature: float | NotGiven = None,
        top_p: float | NotGiven = None,
        max_tokens: int | NotGiven = None,
        seed: int | NotGiven = None,
        stop=None,
        tools=None,
        tool_choice: str | NotGiven = None,
        extra_headers=None,
        extra_body=None,
        timeout: float | None | NotGiven = None,
        **kwargs,
    ):
        url = self._build_endpoint()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)

        payload = {
            "model": self.model,
            "messages": messages or [],
        }
        if isinstance(stream, bool):
            payload["stream"] = stream
        if isinstance(temperature, (int, float)):
            payload["temperature"] = temperature
        if isinstance(top_p, (int, float)):
            payload["top_p"] = top_p
        if isinstance(max_tokens, int):
            payload["max_tokens"] = max_tokens
        if stop not in (None, NotGiven()):
            payload["stop"] = stop
        if tools not in (None, NotGiven()):
            payload["tools"] = tools
        if tool_choice not in (None, NotGiven()):
            payload["tool_choice"] = tool_choice
        if isinstance(extra_body, dict):
            payload.update(extra_body)

        to = self.timeout if timeout in (None, NotGiven()) else timeout
        
        # 添加重试机制（最多重试2次）
        max_retries = 2
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(
                    url, 
                    headers=headers, 
                    data=json.dumps(payload), 
                    timeout=to, 
                    stream=bool(payload.get("stream", False))
                )
                resp.raise_for_status()
                break  # 成功则跳出重试循环
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                last_exception = e
                if attempt < max_retries:
                    print(f"API request timeout (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                    continue
                else:
                    # 最后一次重试也失败，抛出异常
                    raise requests.exceptions.ReadTimeout(
                        f"Request timed out after {max_retries + 1} attempts. "
                        f"Timeout: {to}s per attempt. "
                        f"Last error: {str(e)}",
                        request=e.request
                    ) from e
            except requests.exceptions.RequestException as e:
                # 其他请求异常，不重试
                raise

        if payload.get("stream"):
            full = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    s = line.decode('utf-8')
                except Exception:
                    continue
                if not s.startswith('data: '):
                    continue
                data = s[6:]
                if data == '[DONE]':
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = obj.get('choices', [{}])[0].get('delta', {})
                if 'content' in delta:
                    full += delta['content']
            return full
        else:
            obj = resp.json()
            return obj.get('choices', [{}])[0].get('message', {}).get('content', "")
