"""
Gemini AI 交易模型
使用 Google Gemini API
"""
import httpx
import logging
from typing import Dict, List, Optional
from .base_ai import AITradingModel, TradingDecision

logger = logging.getLogger(__name__)


class GeminiTrader(AITradingModel):
    """Gemini AI 交易员"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp", **kwargs):
        """
        初始化 Gemini 交易员
        
        Args:
            api_key: Google API 密钥
            model: Gemini 模型版本
        """
        super().__init__(
            model_name=f"Gemini ({model.split('-')[1].capitalize()})",
            api_key=api_key,
            **kwargs
        )
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    async def analyze_market(
        self,
        coin: str,
        market_data: Dict,
        orderbook: Dict,
        recent_trades: List[Dict],
        position_info: Optional[Dict] = None
    ) -> tuple[TradingDecision, float, str]:
        """
        使用 Gemini 分析市场
        
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
                    f"{self.api_url}?key={self.api_key}",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "contents": [{
                            "role": "user",
                            "parts": [{
                                "text": prompt
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 4096,
                            "topP": 0.8,
                            "topK": 40
                        },
                        "safetySettings": [
                            {
                                "category": "HARM_CATEGORY_HARASSMENT",
                                "threshold": "BLOCK_NONE"
                            },
                            {
                                "category": "HARM_CATEGORY_HATE_SPEECH",
                                "threshold": "BLOCK_NONE"
                            },
                            {
                                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                "threshold": "BLOCK_NONE"
                            },
                            {
                                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                "threshold": "BLOCK_NONE"
                            }
                        ]
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # 安全解析响应
                try:
                    candidate = result["candidates"][0]
                    content = candidate.get("content", {})
                    
                    # 尝试多种响应格式
                    if "parts" in content and len(content["parts"]) > 0:
                        ai_response = content["parts"][0]["text"]
                    elif "text" in content:
                        ai_response = content["text"]
                    else:
                        logger.error(f"❌ Gemini 响应格式不匹配: {content}")
                        return TradingDecision.HOLD, 0.0, f"无法提取AI响应文本"
                    
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"❌ Gemini 响应解析失败: {e}, 原始响应: {result}")
                    return TradingDecision.HOLD, 0.0, f"响应格式错误"
                
                decision, confidence, reasoning = self.parse_ai_response(ai_response)
                self.record_ai_response(coin, decision, confidence, reasoning, ai_response)
                
                return decision, confidence, reasoning
            else:
                error_detail = response.text
                logger.error(f"❌ Gemini API 错误: {response.status_code} - {error_detail}")
                return TradingDecision.HOLD, 0.0, f"API 调用失败"
        
        except httpx.TimeoutException as e:
            logger.error(f"⏱️ Gemini API 超时: {e}")
            return TradingDecision.HOLD, 0.0, f"API 调用超时"
        except Exception as e:
            logger.error(f"❌ Gemini 分析失败: {e}", exc_info=True)
            return TradingDecision.HOLD, 0.0, f"分析异常: {str(e)}"

