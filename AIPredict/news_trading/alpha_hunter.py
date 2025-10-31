"""
Alpha Hunter - 用户授权的自动交易代理
允许用户授权 AI Agent 在 Hyperliquid 上进行自动交易
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from trading.hyperliquid.client import HyperliquidClient
from config.settings import settings
from news_trading.news_analyzer import NewsAnalyzer

logger = logging.getLogger(__name__)


class AlphaHunterConfig:
    """Alpha Hunter 配置"""
    
    def __init__(
        self,
        user_address: str,
        agent_private_key: str,
        monitored_coins: List[str],
        margin_per_coin: Dict[str, float],  # 每个币种的保证金（逐仓）
        leverage_range: tuple = (10, 50),  # 杠杆范围
    ):
        self.user_address = user_address
        self.agent_private_key = agent_private_key
        self.monitored_coins = monitored_coins
        self.margin_per_coin = margin_per_coin
        self.leverage_range = leverage_range
        self.created_at = datetime.now()
        self.is_active = False


class AlphaHunter:
    """Alpha Hunter 主类 - 管理用户授权的自动交易"""
    
    def __init__(self):
        self.configs: Dict[str, AlphaHunterConfig] = {}  # user_address -> config
        self.agent_clients: Dict[str, HyperliquidClient] = {}  # user_address -> client
        self.news_analyzer: Optional[NewsAnalyzer] = None
        self.is_running = False
        
    async def initialize(self):
        """初始化 Alpha Hunter"""
        try:
            # 初始化 Grok AI（用于新闻分析）
            from ai_models.grok_trader import GrokTrader
            grok_ai = GrokTrader(
                api_key=settings.grok_api_key,
                model=settings.grok_model
            )
            
            # 初始化新闻分析器
            self.news_analyzer = NewsAnalyzer(
                ai_trader=grok_ai,
                ai_name="grok",
                min_confidence=60.0
            )
            logger.info("✅ Alpha Hunter 初始化成功")
            
        except Exception as e:
            logger.error(f"❌ Alpha Hunter 初始化失败: {e}")
            raise
    
    async def register_user(
        self,
        user_address: str,
        agent_private_key: str,
        monitored_coins: List[str],
        margin_per_coin: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        注册用户配置
        
        Args:
            user_address: 用户主账户地址
            agent_private_key: Agent 私钥（由前端生成并授权）
            monitored_coins: 监控的币种列表
            margin_per_coin: 每个币种的保证金配置
            
        Returns:
            注册结果
        """
        try:
            logger.info(f"📝 注册 Alpha Hunter 用户: {user_address[:10]}...")
            
            # 创建配置
            config = AlphaHunterConfig(
                user_address=user_address,
                agent_private_key=agent_private_key,
                monitored_coins=monitored_coins,
                margin_per_coin=margin_per_coin
            )
            
            # 创建 Agent 客户端（使用主网）
            agent_client = await HyperliquidClient.create_agent_client(
                agent_private_key=agent_private_key,
                account_address=user_address,
                testnet=False  # Alpha Hunter 始终使用主网
            )
            
            # 验证账户余额
            account_info = await agent_client.get_account_info()
            balance = float(account_info.get("withdrawable", 0))
            logger.info(f"💰 用户账户余额: {balance} USDC")
            
            # 验证保证金配置（确保所有值都是数字类型）
            total_margin = sum(float(v) for v in margin_per_coin.values())
            if total_margin > balance:
                return {
                    "status": "error",
                    "message": f"保证金总额 ({total_margin} USDC) 超过账户余额 ({balance} USDC)"
                }
            
            # 保存配置
            self.configs[user_address] = config
            self.agent_clients[user_address] = agent_client
            
            logger.info(f"✅ 用户注册成功: {user_address[:10]}...")
            logger.info(f"   监控币种: {monitored_coins}")
            logger.info(f"   保证金配置: {margin_per_coin}")
            
            return {
                "status": "ok",
                "user_address": user_address,
                "monitored_coins": monitored_coins,
                "total_margin": total_margin,
                "balance": balance
            }
            
        except Exception as e:
            logger.error(f"❌ 注册用户失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def add_monitored_coin(
        self,
        user_address: str,
        coin: str,
        margin: float
    ) -> Dict[str, Any]:
        """
        为已注册用户添加新的监控币种
        
        Args:
            user_address: 用户地址
            coin: 币种符号
            margin: 该币种的保证金
            
        Returns:
            操作结果
        """
        try:
            # 检查用户是否已注册
            config = self.configs.get(user_address)
            if not config:
                return {"status": "error", "message": "用户未注册，请先完成 Approve & Start"}
            
            # 检查币种是否已存在
            if coin in config.monitored_coins:
                return {"status": "error", "message": f"{coin} 已在监控列表中"}
            
            # 获取账户余额
            agent_client = self.agent_clients.get(user_address)
            if not agent_client:
                return {"status": "error", "message": "Agent 客户端未找到"}
            
            account_info = await agent_client.get_account_info()
            balance = float(account_info.get("withdrawable", 0))
            
            # 计算新的总保证金
            current_total_margin = sum(float(v) for v in config.margin_per_coin.values())
            new_total_margin = current_total_margin + margin
            
            if new_total_margin > balance:
                return {
                    "status": "error",
                    "message": f"新增保证金后总额 ({new_total_margin} USDC) 超过账户余额 ({balance} USDC)"
                }
            
            # 添加币种
            config.monitored_coins.append(coin)
            config.margin_per_coin[coin] = margin
            
            logger.info(f"✅ 用户 {user_address[:10]}... 添加监控币种: {coin} (保证金: {margin} USDC)")
            logger.info(f"   当前监控币种: {config.monitored_coins}")
            logger.info(f"   总保证金: {new_total_margin} USDC / {balance} USDC")
            
            return {
                "status": "ok",
                "message": f"成功添加 {coin} 到监控列表",
                "monitored_coins": config.monitored_coins,
                "total_margin": new_total_margin,
                "balance": balance
            }
            
        except Exception as e:
            logger.error(f"❌ 添加监控币种失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start_monitoring(self, user_address: str) -> Dict[str, Any]:
        """开始监控（激活 Alpha Hunter）"""
        try:
            config = self.configs.get(user_address)
            if not config:
                return {"status": "error", "message": "用户未注册"}
            
            config.is_active = True
            self.is_running = True
            
            logger.info(f"🚀 Alpha Hunter 开始监控: {user_address[:10]}...")
            
            return {
                "status": "ok",
                "message": "Alpha Hunter 已激活",
                "monitored_coins": config.monitored_coins
            }
            
        except Exception as e:
            logger.error(f"❌ 开始监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def stop_monitoring(self, user_address: str) -> Dict[str, Any]:
        """停止监控"""
        try:
            config = self.configs.get(user_address)
            if not config:
                return {"status": "error", "message": "用户未注册"}
            
            config.is_active = False
            
            # 检查是否还有其他活跃用户
            active_users = [c for c in self.configs.values() if c.is_active]
            if not active_users:
                self.is_running = False
            
            logger.info(f"⏸️  Alpha Hunter 停止监控: {user_address[:10]}...")
            
            return {"status": "ok", "message": "Alpha Hunter 已停止"}
            
        except Exception as e:
            logger.error(f"❌ 停止监控失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def handle_news_trigger(
        self,
        coin_symbol: str,
        news_content: str,
        news_source: str
    ) -> List[Dict[str, Any]]:
        """
        处理新闻触发的交易
        
        Args:
            coin_symbol: 币种符号
            news_content: 新闻内容
            news_source: 新闻来源
            
        Returns:
            所有用户的交易结果列表
        """
        results = []
        
        try:
            # 遍历所有活跃用户
            for user_address, config in self.configs.items():
                if not config.is_active:
                    continue
                
                # 检查用户是否监控该币种
                if coin_symbol not in config.monitored_coins:
                    continue
                
                # 获取该币种的保证金配置
                margin = config.margin_per_coin.get(coin_symbol, 0)
                if margin <= 0:
                    logger.warning(f"⚠️  {user_address[:10]}... 未配置 {coin_symbol} 的保证金，跳过")
                    continue
                
                logger.info(f"📢 Alpha Hunter 处理新闻触发:")
                logger.info(f"   用户: {user_address[:10]}...")
                logger.info(f"   币种: {coin_symbol}")
                logger.info(f"   保证金: {margin} USDC")
                
                # 调用 AI 分析
                result = await self._execute_trade_for_user(
                    user_address=user_address,
                    coin_symbol=coin_symbol,
                    news_content=news_content,
                    news_source=news_source,
                    margin=margin
                )
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ handle_news_trigger 失败: {e}")
            return []
    
    async def _execute_trade_for_user(
        self,
        user_address: str,
        coin_symbol: str,
        news_content: str,
        news_source: str,
        margin: float
    ) -> Dict[str, Any]:
        """为单个用户执行交易"""
        try:
            # 获取 Agent 客户端
            agent_client = self.agent_clients.get(user_address)
            if not agent_client:
                return {
                    "status": "error",
                    "user_address": user_address,
                    "message": "Agent 客户端未找到"
                }
            
            # 调用 Grok AI 分析
            if not self.news_analyzer:
                return {
                    "status": "error",
                    "user_address": user_address,
                    "message": "NewsAnalyzer 未初始化"
                }
            
            ai_start_time = datetime.now()
            
            analysis_result = await self.news_analyzer.analyze_with_grok(
                coin_symbol=coin_symbol,
                news_content=news_content,
                news_source=news_source
            )
            
            ai_duration = (datetime.now() - ai_start_time).total_seconds()
            
            if not analysis_result or "error" in analysis_result:
                return {
                    "status": "error",
                    "user_address": user_address,
                    "message": f"AI 分析失败: {analysis_result.get('error', 'Unknown')}"
                }
            
            decision = analysis_result.get("decision", "HOLD")
            confidence = analysis_result.get("confidence", 50)
            leverage = analysis_result.get("leverage", 20)
            
            logger.info(f"🤖 Grok AI 决策:")
            logger.info(f"   决策: {decision}")
            logger.info(f"   信心: {confidence}%")
            logger.info(f"   杠杆: {leverage}x")
            logger.info(f"   分析耗时: {ai_duration:.2f}s")
            
            # 如果决策是 HOLD，不执行交易
            if decision == "HOLD":
                return {
                    "status": "skipped",
                    "user_address": user_address,
                    "coin": coin_symbol,
                    "decision": decision,
                    "confidence": confidence,
                    "ai_duration": ai_duration
                }
            
            # 执行交易
            trade_result = await self._place_order(
                agent_client=agent_client,
                coin_symbol=coin_symbol,
                decision=decision,
                leverage=leverage,
                margin=margin
            )
            
            return {
                "status": "ok",
                "user_address": user_address,
                "coin": coin_symbol,
                "decision": decision,
                "confidence": confidence,
                "leverage": leverage,
                "margin": margin,
                "ai_duration": ai_duration,
                "trade_result": trade_result
            }
            
        except Exception as e:
            logger.error(f"❌ _execute_trade_for_user 失败: {e}")
            return {
                "status": "error",
                "user_address": user_address,
                "message": str(e)
            }
    
    async def _place_order(
        self,
        agent_client: HyperliquidClient,
        coin_symbol: str,
        decision: str,
        leverage: int,
        margin: float
    ) -> Dict[str, Any]:
        """使用 Agent 客户端下单"""
        try:
            # 获取市场价格
            market_data = await agent_client.get_market_data(coin_symbol)
            if not market_data:
                return {"status": "error", "message": "无法获取市场数据"}
            
            current_price = market_data.get("mid_price", 0)
            
            # 计算持仓大小
            position_value = margin * leverage
            size = position_value / current_price
            
            # 确定方向
            is_buy = decision == "BUY"
            
            # 设置杠杆（逐仓模式）
            await agent_client.update_leverage(coin_symbol, leverage, is_cross=False)
            
            # 市价单开仓
            order_result = await agent_client.place_order(
                symbol=coin_symbol,
                side="buy" if is_buy else "sell",
                price=current_price,
                size=size,
                leverage=leverage,
                order_type="market",
                reduce_only=False
            )
            
            logger.info(f"✅ Alpha Hunter 订单执行成功:")
            logger.info(f"   币种: {coin_symbol}")
            logger.info(f"   方向: {'做多' if is_buy else '做空'}")
            logger.info(f"   杠杆: {leverage}x")
            logger.info(f"   保证金: {margin} USDC")
            logger.info(f"   持仓价值: {position_value} USDC")
            
            return {
                "status": "ok",
                "order_result": order_result,
                "price": current_price,
                "size": size,
                "position_value": position_value
            }
            
        except Exception as e:
            logger.error(f"❌ _place_order 失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_user_status(self, user_address: str) -> Dict[str, Any]:
        """获取用户状态"""
        config = self.configs.get(user_address)
        if not config:
            return {"status": "error", "message": "用户未注册"}
        
        return {
            "status": "ok",
            "user_address": user_address,
            "monitored_coins": config.monitored_coins,
            "margin_per_coin": config.margin_per_coin,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat()
        }
    
    def get_all_active_coins(self) -> List[str]:
        """获取所有活跃用户监控的币种（去重）"""
        all_coins = set()
        for config in self.configs.values():
            if config.is_active:
                all_coins.update(config.monitored_coins)
        return list(all_coins)


# 全局实例
alpha_hunter = AlphaHunter()

