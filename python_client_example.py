#!/usr/bin/env python3
"""
SciPIP API Python 客户端示例

安装依赖:
pip install aiohttp requests
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Callable, Optional


class SciPIPClient:
    """SciPIP API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.generate_url = f"{base_url}/generate"
        self.health_url = f"{base_url}/health"
    
    async def check_health(self) -> Dict[str, Any]:
        """检查API健康状态"""
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.health_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            raise Exception(f"Health check error: {e}")
    
    async def generate_ideas_stream(
        self, 
        background: str, 
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        生成研究想法（流式响应）
        
        Args:
            background: 研究背景信息
            on_message: 消息处理回调函数
            
        Returns:
            最终结果数据，如果出错则返回None
        """
        payload = {"background": background, "stream": True}
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.generate_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    # 处理流式响应
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                
                                # 调用回调函数
                                if on_message:
                                    on_message(data)
                                
                                # 如果是最终结果，返回
                                if data.get("type") == "final_result":
                                    return data.get("data")
                                
                                # 如果是错误，抛出异常
                                if data.get("type") == "error":
                                    raise Exception(data.get("data", {}).get("message", "Unknown error"))
                                    
                            except json.JSONDecodeError as e:
                                print(f"Failed to parse JSON: {line_str}")
                                continue
                    
                    return None
                    
        except Exception as e:
            print(f"Generation error: {e}")
            return None
    
    async def generate_ideas_sync(self, background: str) -> Optional[Dict[str, Any]]:
        """
        生成研究想法（同步等待最终结果）
        
        Args:
            background: 研究背景信息
            
        Returns:
            最终结果数据
        """
        payload = {"background": background, "stream": False}
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.generate_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    return await response.json()
                    
        except Exception as e:
            print(f"Generation error: {e}")
            return None


class MessageHandler:
    """消息处理器，用于格式化输出"""
    
    def __init__(self):
        self.start_time = time.time()
        self.message_count = 0
    
    def handle_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        self.message_count += 1
        timestamp = time.strftime("%H:%M:%S")
        message_type = data.get("type", "unknown")
        
        print(f"[{timestamp}] ", end="")
        
        if message_type == "query_received":
            background = data.get("data", {}).get("background", "")
            print(f"📥 查询已接收: {background}")
            
        elif message_type == "step_start":
            step = data.get("data", {}).get("step", "")
            message = data.get("data", {}).get("message", "")
            print(f"🔄 步骤开始: {step}")
            if message:
                print(f"   {message}")
            
        elif message_type == "step_complete":
            step = data.get("data", {}).get("step", "")
            message = data.get("data", {}).get("message", "")
            
            if step == "extract_entities":
                entities = data.get("data", {}).get("entities", [])
                print(f"✅ 实体提取完成: {len(entities)} 个实体")
                if entities:
                    print(f"   实体: {', '.join(entities[:5])}{'...' if len(entities) > 5 else ''}")
            
            elif step == "expand_background":
                print(f"✅ 背景扩展完成")
            
            elif step == "brainstorm":
                print(f"✅ 头脑风暴完成")
            
            elif step == "extract_entities_literature":
                entities = data.get("data", {}).get("entities", [])
                print(f"✅ 文献检索实体提取完成: {len(entities)} 个实体")
            
            elif step == "retrieve_literature":
                count = data.get("data", {}).get("related_works_count", 0)
                print(f"✅ 文献检索完成: {count} 篇相关论文")
            
            elif step == "generate_ideas":
                print(f"✅ 想法生成完成")
            
            if message:
                print(f"   {message}")
            
        elif message_type == "final_result":
            print("🎉 最终结果生成完成!")
            result = data.get("data", {})
            initial_count = result.get("initial_ideas_count", 0)
            final_count = result.get("final_ideas_count", 0)
            print(f"   初始想法数: {initial_count}")
            print(f"   详细想法数: {final_count}")
            
        elif message_type == "error":
            step = data.get("data", {}).get("step", "")
            error_msg = data.get("data", {}).get("message", "")
            print(f"❌ 错误 (步骤: {step}): {error_msg}")
            
        else:
            data_str = json.dumps(data.get("data", {}), ensure_ascii=False)[:100]
            print(f"📄 {message_type}: {data_str}...")
    
    def print_summary(self):
        """打印处理摘要"""
        duration = time.time() - self.start_time
        print(f"\n📊 处理摘要:")
        print(f"   总消息数: {self.message_count}")
        print(f"   处理时间: {duration:.2f} 秒")


async def main():
    """主函数示例"""
    client = SciPIPClient()
    handler = MessageHandler()
    
    try:
        # 检查API状态
        print("🔍 检查API状态...")
        health = await client.check_health()
        print(f"✅ API状态: {health['status']}")
        print(f"   服务: {health['service']}")
        print(f"   版本: {health['version']}")
        print(f"   后端就绪: {'是' if health['backend_ready'] else '否'}")
        print()
        
        # 生成研究想法
        background = """
        I am interested in improving the interpretability of deep learning models, 
        especially for vision tasks. I want to understand how neural networks make 
        decisions and provide explanations that are meaningful to end users.
        """
        
        print(f"🚀 生成研究想法...")
        print(f"背景: {background.strip()[:100]}...")
        print()
        
        # 流式处理
        result = await client.generate_ideas_stream(background, handler.handle_message)
        
        if result:
            print()
            print("🎉 研究想法生成完成!")
            print("=" * 60)
            
            ideas = result.get("ideas", [])
            print(f"📋 生成的想法数量: {len(ideas)}")
            print()
            
            for idea in ideas:
                print(f"💡 想法 #{idea['index']}")
                print(f"   简洁版本:")
                print(f"   {idea['concise_idea'][:200]}{'...' if idea['concise_idea'] and len(idea['concise_idea']) > 200 else ''}")
                if idea['idea_in_detail']:
                    print(f"   详细版本:")
                    print(f"   {idea['idea_in_detail'][:200]}{'...' if len(idea['idea_in_detail']) > 200 else ''}")
                print()
        else:
            print("❌ 生成失败")
        
        handler.print_summary()
        
        # 也可以使用同步方式
        print("\n" + "=" * 60)
        print("测试同步API调用...")
        print("=" * 60)
        sync_result = await client.generate_ideas_sync(background)
        if sync_result and sync_result.get("status") == "success":
            print(f"✅ 同步调用成功: 生成 {sync_result.get('initial_ideas_count', 0)} 个想法")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

