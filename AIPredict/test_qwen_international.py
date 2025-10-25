"""
测试阿里云国际版 Qwen API Key
"""
import asyncio
import httpx

async def test_qwen_international_api():
    # 阿里云国际版 API Key
    api_key = "sk-184c0b40c6b74c56be2bf4a3c1380227"
    
    print(f"✓ 测试 API Key (国际版): {api_key[:20]}...")
    
    # 阿里云国际版可能的 API 端点
    endpoints_to_test = [
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    ]
    
    # 尝试多个模型名称
    models_to_test = ["qwen-max", "qwen-plus", "qwen-turbo", "qwen2.5-max"]
    
    test_prompt = "Hello, please respond with 'API test successful' in one sentence."
    
    for endpoint in endpoints_to_test:
        print(f"\n{'='*70}")
        print(f"📡 测试端点: {endpoint}")
        print('='*70)
        
        for model in models_to_test:
            print(f"\n  🔍 测试模型: {model}")
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # OpenAI 兼容格式
                    if "compatible-mode" in endpoint:
                        payload = {
                            "model": model,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": test_prompt
                                }
                            ],
                            "temperature": 0.7,
                            "max_tokens": 100
                        }
                    else:
                        # 阿里云原生格式
                        payload = {
                            "model": model,
                            "input": {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": test_prompt
                                    }
                                ]
                            },
                            "parameters": {
                                "result_format": "message"
                            }
                        }
                    
                    response = await client.post(
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json=payload
                    )
                    
                    print(f"     状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"     ✅ 成功！")
                        
                        # 尝试提取响应内容
                        try:
                            if "compatible-mode" in endpoint:
                                content = result["choices"][0]["message"]["content"]
                                usage = result.get("usage", {})
                            else:
                                content = result["output"]["choices"][0]["message"]["content"]
                                usage = result.get("usage", {})
                            
                            print(f"\n     📝 响应: {content}")
                            print(f"     📊 Tokens: {usage}")
                            print(f"\n🎉 找到可用配置！")
                            print(f"   Endpoint: {endpoint}")
                            print(f"   Model: {model}")
                            return (endpoint, model)
                        except KeyError as e:
                            print(f"     ⚠️ 响应格式异常: {e}")
                            print(f"     原始响应: {result}")
                    else:
                        error = response.json().get('error', {})
                        print(f"     ❌ 错误: {error.get('code', 'N/A')} - {error.get('message', 'N/A')[:50]}")
                        
            except Exception as e:
                print(f"     ⚠️ 异常: {str(e)[:80]}")
    
    print("\n❌ 所有配置均测试失败")
    return None

if __name__ == "__main__":
    result = asyncio.run(test_qwen_international_api())
    if result:
        endpoint, model = result
        print(f"\n✨ 推荐配置:")
        print(f"   API Endpoint: {endpoint}")
        print(f"   Model: {model}")
    else:
        print("\n⚠️ 建议:")
        print("1. 确认 API Key 是否激活")
        print("2. 检查国际版控制台的 API 文档")
        print("3. 确认是否需要在特定区域（如新加坡、美国）使用")

