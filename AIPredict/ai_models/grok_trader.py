"""
Grok AI 交易模型
使用 xAI Grok API
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class GrokTrader(AITradingModel):
    """Grok AI 交易员"""
    
    def __init__(self, api_key: str, model: str = "grok-4", **kwargs):
        """
        初始化 Grok 交易员
        
        Args:
            api_key: xAI API 密钥
            model: Grok 模型版本
        """
        super().__init__(
            model_name=f"Grok ({model.split('-')[1].capitalize() if '-' in model else 'Beta'})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = "https://api.x.ai/v1/chat/completions"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        使用 Grok 分析市场
        
        Args:
            coin: 币种
            market_data: 市场数据
            orderbook: 订单簿
            recent_trades: 最近交易
            
        Returns:
            (决策, 置信度, 理由)
        """
        position_info = self.positions.get(coin)
        prompt = self.create_market_prompt(coin, market_data, orderbook, position_info)
        
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:  # 增加timeout
                    response = await client.post(
                        self.api_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "你是一个专业的加密货币合约交易分析师。"
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ],
                            "temperature": 0.7,
                            "max_tokens": 500
                        }
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result["choices"][0]["message"]["content"]
                    
                    decision, confidence, reasoning = self.parse_ai_response(ai_response)
                    self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                    
                    if attempt > 0:
                        print(f"✅ Grok API 重试成功（第{attempt+1}次尝试）")
                    
                    return decision, confidence, reasoning
                else:
                    error_detail = response.text
                    print(f"❌ Grok API 错误（尝试{attempt+1}/{max_retries}）: {response.status_code} - {error_detail[:200]}")
                    
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)  # 指数退避：2秒、4秒
                        continue
                    
                    return TradingDecision.HOLD, 0.0, f"API 调用失败: {response.status_code}"
            
            except httpx.TimeoutException as e:
                print(f"⏱️ Grok API 超时（尝试{attempt+1}/{max_retries}）: {str(e)}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return TradingDecision.HOLD, 0.0, f"API 超时"
            
            except Exception as e:
                print(f"❌ Grok 分析异常（尝试{attempt+1}/{max_retries}）: {type(e).__name__}: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                    continue
                return TradingDecision.HOLD, 0.0, f"分析异常: {str(e)[:100]}"
        
        return TradingDecision.HOLD, 0.0, f"重试失败"

