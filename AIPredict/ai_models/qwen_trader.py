"""
Qwen AI 交易模型
使用阿里云通义千问 API
"""
import httpx
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision


class QwenTrader(AITradingModel):
    """Qwen AI 交易员"""
    
    def __init__(self, api_key: str, model: str = "qwen-turbo", use_international: bool = False, **kwargs):
        """
        初始化 Qwen 交易员
        
        Args:
            api_key: 阿里云 API 密钥
            model: Qwen 模型版本 (qwen-turbo, qwen-max, qwen-plus)
            use_international: 是否使用国际版API (默认False为国内版)
        """
        super().__init__(
            model_name=f"Qwen ({model.split('-')[1].capitalize()})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        # 根据是否国际版选择API端点
        if use_international:
            self.api_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        else:
            self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        使用 Qwen 分析市场
        
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
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
                
                return decision, confidence, reasoning
            else:
                error_detail = response.text
                print(f"Qwen API 错误: {response.status_code} - {error_detail}")
                return TradingDecision.HOLD, 0.0, f"API 调用失败"
        
        except Exception as e:
            print(f"Qwen 分析失败: {e}")
            return TradingDecision.HOLD, 0.0, f"分析异常: {str(e)}"

