"""
AI消息分析器
AI Message Analyzer
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

# 导入现有AI模型
from ai_models.claude_trader import ClaudeTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.deepseek_trader import DeepSeekTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.grok_trader import GrokTrader
from ai_models.qwen_trader import QwenTrader

from .message_listeners.base_listener import ListingMessage
from .config import TradingMode, AIModeConfig

logger = logging.getLogger(__name__)


@dataclass
class TradingStrategy:
    """AI分析后的交易策略"""
    should_trade: bool          # 是否应该交易
    direction: str              # 方向: "long" or "short"
    leverage: int               # 杠杆倍数 (10-40)
    margin: float               # 保证金（USDT）
    stop_loss_pct: float        # 止损百分比
    take_profit_pct: float      # 止盈百分比
    confidence: float           # 信心度 (0-100)
    reasoning: str              # AI推理过程
    ai_name: str                # 使用的AI名称


class NewsAnalyzer:
    """消息分析器"""
    
    def __init__(
        self,
        ai_trader,
        ai_name: str,
        min_confidence: float = 60.0
    ):
        """
        初始化分析器
        
        Args:
            ai_trader: AI交易模型实例
            ai_name: AI名称
            min_confidence: 最小信心度阈值
        """
        self.ai_trader = ai_trader
        self.ai_name = ai_name
        self.min_confidence = min_confidence
    
    async def analyze(self, message: ListingMessage) -> Optional[TradingStrategy]:
        """
        分析消息并生成交易策略
        
        Args:
            message: 上币消息
            
        Returns:
            交易策略或None
        """
        try:
            # 构建AI提示词
            prompt = self._create_analysis_prompt(message)
            
            # 调用AI分析（使用现有AI模型的analyze_market接口需要市场数据，
            # 这里我们直接构造一个简单的分析请求）
            logger.info(f"🤖 [{self.ai_name}] 开始分析消息: {message.coin_symbol}")
            
            # 由于现有AI模型需要市场数据，我们创建一个简化的分析方法
            analysis_result = await self._simple_ai_call(prompt)
            
            if not analysis_result:
                return None
            
            # 解析AI响应
            strategy = self._parse_ai_response(analysis_result, message)
            
            if strategy and strategy.confidence >= self.min_confidence:
                logger.info(
                    f"✅ [{self.ai_name}] 分析完成: {strategy.direction} "
                    f"{strategy.leverage}x, 信心度 {strategy.confidence:.1f}%"
                )
                return strategy
            else:
                logger.info(f"⚠️ [{self.ai_name}] 信心度不足，不建议交易")
                return None
        
        except Exception as e:
            logger.error(f"❌ [{self.ai_name}] 分析消息时出错: {e}", exc_info=True)
            return None
    
    def _create_analysis_prompt(self, message: ListingMessage) -> str:
        """构建AI分析提示词（极速版）"""
        from config.settings import settings
        
        return f"""Crypto listing: {message.coin_symbol} on {message.source}
Reliability: {message.reliability_score:.0%}
Message: {message.raw_message[:150]}

Decide FAST:
TRADE: YES/NO
DIRECTION: LONG/SHORT
LEVERAGE: [{settings.news_min_leverage}-{settings.news_max_leverage}] (confidence-based: 60%={settings.news_min_leverage}x, 100%={settings.news_max_leverage}x)
CONFIDENCE: [0-100]
REASONING: [max 10 words]

Rules:
- Leverage: scales with confidence (60%→{settings.news_min_leverage}x, 100%→{settings.news_max_leverage}x)
- Margin: {settings.news_min_margin_pct*100:.0f}%-{settings.news_max_margin_pct*100:.0f}% of balance (confidence-based)
- Stop loss: {settings.news_stop_loss_pct*100:.0f}% (fixed)
- Take profit: {settings.news_take_profit_pct*100:.0f}% (fixed)
- Only trade if confidence ≥ 60%
"""
    
    async def _simple_ai_call(self, prompt: str) -> Optional[str]:
        """简化的AI调用（不依赖市场数据）"""
        try:
            # 这里我们需要根据不同AI模型类型调用其API
            # 由于现有AI类的analyze_market需要市场数据，我们直接调用AI API
            
            # 对于支持的AI模型，直接构造API请求
            if hasattr(self.ai_trader, 'api_url') and hasattr(self.ai_trader, 'api_key'):
                import httpx
                
                # 根据不同AI类型构造请求
                if isinstance(self.ai_trader, ClaudeTrader):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            self.ai_trader.api_url,
                            headers={
                                "x-api-key": self.ai_trader.api_key,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json"
                            },
                            json={
                                "model": self.ai_trader.model,
                                "max_tokens": 100,  # 极速模式：最小token
                                "messages": [{"role": "user", "content": prompt}]
                            }
                        )
                        if response.status_code == 200:
                            result = response.json()
                            return result["content"][0]["text"]
                
                elif isinstance(self.ai_trader, (GPTTrader, DeepSeekTrader, GrokTrader)):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            self.ai_trader.api_url,
                            headers={
                                "Authorization": f"Bearer {self.ai_trader.api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": self.ai_trader.model,
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.7,
                                "max_tokens": 100  # 极速模式：最小token
                            }
                        )
                        if response.status_code == 200:
                            result = response.json()
                            return result["choices"][0]["message"]["content"]
                
                elif isinstance(self.ai_trader, QwenTrader):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            self.ai_trader.api_url,
                            headers={
                                "Authorization": f"Bearer {self.ai_trader.api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": self.ai_trader.model,
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.7,
                                "max_tokens": 100  # 极速模式：最小token
                            }
                        )
                        if response.status_code == 200:
                            result = response.json()
                            return result["choices"][0]["message"]["content"]
                
                elif isinstance(self.ai_trader, GeminiTrader):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{self.ai_trader.api_url}?key={self.ai_trader.api_key}",
                            headers={"Content-Type": "application/json"},
                            json={
                                "contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.7}  # Gemini 2.5 Pro是推理模型，需要大量tokens（思考+输出）
                            }
                        )
                        if response.status_code == 200:
                            result = response.json()
                            # Gemini 2.5 Pro有不同的响应结构
                            try:
                                candidate = result["candidates"][0]
                                content = candidate.get("content", {})
                                
                                # 检查是否有parts（标准格式）
                                if "parts" in content and len(content["parts"]) > 0:
                                    return content["parts"][0]["text"]
                                
                                # Gemini 2.5 Pro可能没有parts，只有role
                                # 这种情况下所有token都用于思考，没有实际输出
                                logger.warning(f"⚠️  [{self.ai_name}] Gemini响应无文本输出（可能全是思考token）")
                                logger.debug(f"Gemini响应结构: {result}")
                                return None
                            
                            except (KeyError, IndexError) as e:
                                logger.error(f"❌ [{self.ai_name}] Gemini响应解析失败: {e}")
                                logger.debug(f"原始响应: {result}")
                                return None
            
            return None
        
        except Exception as e:
            logger.error(f"❌ [{self.ai_name}] AI调用失败: {e}")
            return None
    
    def _parse_ai_response(self, response: str, message: ListingMessage) -> Optional[TradingStrategy]:
        """解析AI响应"""
        try:
            lines = response.strip().split("\n")
            parsed = {}
            
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    parsed[key.strip().upper()] = value.strip()
            
            # 🔍 调试日志：记录AI原始响应
            logger.debug(f"🔍 [{self.ai_name}] 原始响应:\n{response}")
            logger.debug(f"🔍 [{self.ai_name}] 解析结果: {parsed}")
            
            # 检查是否应该交易
            should_trade = parsed.get("TRADE", "NO").upper() == "YES"
            
            if not should_trade:
                return None
            
            # 解析交易参数
            from config.settings import settings
            
            direction_raw = parsed.get("DIRECTION", "LONG").upper()
            leverage = int(float(parsed.get("LEVERAGE", 20)))
            position_size_pct = float(parsed.get("POSITION_SIZE_PCT", 0.2))  # 已废弃，保留用于向后兼容
            stop_loss = float(parsed.get("STOP_LOSS", settings.news_stop_loss_pct))
            take_profit = float(parsed.get("TAKE_PROFIT", settings.news_take_profit_pct))
            confidence = float(parsed.get("CONFIDENCE", 50))
            reasoning = parsed.get("REASONING", "AI analysis completed")
            
            # 解析方向（支持多种格式）
            # LONG/BUY -> long, SHORT/SELL -> short
            if "LONG" in direction_raw or "BUY" in direction_raw:
                direction = "long"
            elif "SHORT" in direction_raw or "SELL" in direction_raw:
                direction = "short"
            else:
                logger.warning(f"⚠️ [{self.ai_name}] 无法识别方向: {direction_raw}，默认为LONG")
                direction = "long"
            
            logger.info(f"📍 [{self.ai_name}] 方向解析: {direction_raw} → {direction}")
            
            # 限制范围（从环境变量读取）
            leverage = max(settings.news_min_leverage, min(leverage, settings.news_max_leverage))
            position_size_pct = 1.0  # 已废弃，保留用于向后兼容
            stop_loss = settings.news_stop_loss_pct  # 从配置读取
            take_profit = settings.news_take_profit_pct  # 从配置读取
            
            # 注意：这里的margin字段现在表示"仓位比例"，实际保证金将在执行时根据账户余额计算
            return TradingStrategy(
                should_trade=True,
                direction=direction,
                leverage=leverage,
                margin=position_size_pct,  # 存储仓位比例，不是实际金额
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit,
                confidence=confidence,
                reasoning=reasoning,
                ai_name=self.ai_name
            )
        
        except Exception as e:
            logger.error(f"❌ [{self.ai_name}] 解析AI响应失败: {e}")
            logger.debug(f"原始响应: {response}")
            return None


def create_news_analyzer(ai_name: str, api_key: str) -> Optional[NewsAnalyzer]:
    """
    创建消息分析器
    
    Args:
        ai_name: AI名称 (claude, gpt, deepseek, gemini, grok, qwen)
        api_key: API密钥
        
    Returns:
        NewsAnalyzer实例或None
    """
    ai_name_lower = ai_name.lower()
    
    try:
        if ai_name_lower == "claude":
            trader = ClaudeTrader(api_key=api_key)
            return NewsAnalyzer(trader, "Claude")
        
        elif ai_name_lower in ["gpt", "gpt4"]:
            from config.settings import settings
            trader = GPTTrader(
                api_key=api_key,
                model=settings.gpt_model
            )
            return NewsAnalyzer(trader, "GPT-4")
        
        elif ai_name_lower == "deepseek":
            trader = DeepSeekTrader(api_key=api_key)
            return NewsAnalyzer(trader, "DeepSeek")
        
        elif ai_name_lower == "gemini":
            from config.settings import settings
            trader = GeminiTrader(
                api_key=api_key,
                model=settings.gemini_model
            )
            return NewsAnalyzer(trader, "Gemini")
        
        elif ai_name_lower == "grok":
            from config.settings import settings
            trader = GrokTrader(
                api_key=api_key,
                model=settings.grok_model
            )
            return NewsAnalyzer(trader, "Grok")
        
        elif ai_name_lower == "qwen":
            from config.settings import settings
            trader = QwenTrader(
                api_key=api_key,
                model=settings.qwen_model,
                use_international=settings.qwen_use_international
            )
            return NewsAnalyzer(trader, "Qwen")
        
        else:
            logger.error(f"❌ 不支持的AI模型: {ai_name}")
            return None
    
    except Exception as e:
        logger.error(f"❌ 创建{ai_name}分析器失败: {e}")
        return None

