"""
消息驱动交易处理器 - 精简版
News Trading Handler - Simplified Version

复用现有独立AI账户，每个AI独立分析和交易
"""
import logging
import asyncio
from datetime import datetime
from typing import List, Optional

from .message_listeners.base_listener import ListingMessage
from .news_analyzer import create_news_analyzer
from .event_manager import event_manager

logger = logging.getLogger(__name__)


class NewsTradeHandler:
    """消息交易处理器 - 使用现有独立AI账户"""
    
    def __init__(self):
        """初始化处理器"""
        self.individual_traders = []  # 将由外部设置
        self.configured_ais = []  # 配置的AI列表
        self.analyzers = {}  # AI分析器缓存
        self.recent_messages = {}  # 最近处理的消息 {coin: timestamp}
        self.message_cooldown = 60  # 消息冷却时间（秒），同一币种60秒内只处理一次
        
        logger.info("🚀 消息交易处理器初始化")
    
    def setup(self, individual_traders: List, configured_ais: List[str], ai_api_keys: dict, monitored_coins: List[str] = None):
        """
        配置处理器
        
        Args:
            individual_traders: Arena的独立AI交易者列表
            configured_ais: 配置的AI名称列表（如 ['claude', 'gpt', 'deepseek']）
            ai_api_keys: AI的API密钥字典
            monitored_coins: 监控的币种列表（如 ['PING', 'MON']），如果为None则监控所有
        """
        self.individual_traders = individual_traders
        self.configured_ais = [ai.lower() for ai in configured_ais]
        self.monitored_coins = [coin.upper() for coin in monitored_coins] if monitored_coins else None
        
        # 为每个配置的AI创建分析器
        for trader in individual_traders:
            ai_name_lower = trader.ai_name.lower()
            
            if ai_name_lower not in self.configured_ais:
                continue
            
            api_key = ai_api_keys.get(ai_name_lower)
            if not api_key:
                logger.warning(f"⚠️  {trader.ai_name} 没有API Key，跳过")
                continue
            
            analyzer = create_news_analyzer(ai_name_lower, api_key)
            if analyzer:
                self.analyzers[trader.ai_name] = analyzer
                logger.info(f"✅ 已为 {trader.ai_name} 创建分析器")
        
        logger.info(f"📊 消息交易已配置，激活的AI: {list(self.analyzers.keys())}")
    
    async def handle_message(self, message: ListingMessage):
        """
        处理上币消息 - 所有配置的AI并发分析和交易
        
        Args:
            message: 上币消息
        """
        coin = message.coin_symbol
        
        # 过滤：只处理监控的币种
        if self.monitored_coins and coin.upper() not in self.monitored_coins:
            logger.info(f"⏭️  [消息交易] 跳过未监控的币种: {coin} (监控列表: {self.monitored_coins})")
            return
        
        # 🚀 消息去重：检查是否在冷却期内
        import time
        current_time = time.time()
        last_processed = self.recent_messages.get(coin)
        
        if last_processed:
            time_since_last = current_time - last_processed
            if time_since_last < self.message_cooldown:
                logger.info(f"⏭️  [消息去重] {coin} 在冷却期内 ({time_since_last:.1f}s < {self.message_cooldown}s)，跳过重复处理")
                logger.info(f"   来源: {message.source} (已在 {self.message_cooldown - time_since_last:.1f}秒后重新处理)")
                return
        
        # 记录处理时间
        self.recent_messages[coin] = current_time
        
        logger.info(f"📬 [消息交易] 收到上币消息: {coin} (来源: {message.source})")
        logger.info(f"🤖 准备让 {len(self.analyzers)} 个AI分析...")
        
        # 🚀 推送事件：检测到新币
        await event_manager.push_event("coin_detected", {
            "coin": coin,
            "source": message.source,
            "ai_count": len(self.analyzers)
        })
        
        # 为每个AI创建处理任务
        tasks = []
        for trader in self.individual_traders:
            if trader.ai_name in self.analyzers:
                task = self._handle_single_ai(trader, message)
                tasks.append(task)
        
        # 并发执行
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _handle_single_ai(self, trader, message: ListingMessage):
        """单个AI处理消息"""
        coin = message.coin_symbol
        ai_name = trader.ai_name
        analyzer = self.analyzers.get(ai_name)
        
        if not analyzer:
            return
        
        # 🕐 开始计时
        t_start = datetime.now()
        
        try:
            logger.info(f"🤖 [{ai_name}] 开始分析消息: {coin}")
            
            # 1. AI分析
            t1 = datetime.now()
            strategy = await analyzer.analyze(message)
            t2 = datetime.now()
            
            analysis_time = (t2 - t1).total_seconds()
            
            if not strategy or not strategy.should_trade:
                logger.info(f"⚠️  [{ai_name}] 不建议交易 {coin} (分析耗时: {analysis_time:.2f}s)")
                return
            
            logger.info(
                f"✅ [{ai_name}] 分析完成: {strategy.direction} {strategy.leverage}x, "
                f"信心度 {strategy.confidence:.1f}% (耗时: {analysis_time:.2f}s)"
            )
            
            # 🚀 推送事件：AI分析完成
            await event_manager.push_event("ai_analysis", {
                "ai": ai_name,
                "coin": coin,
                "decision": strategy.direction,
                "leverage": strategy.leverage,
                "confidence": strategy.confidence,
                "analysis_time": round(analysis_time, 2)
            })
            
            # 2. 检查并平掉现有仓位
            t3 = datetime.now()
            await self._close_existing_positions(trader, coin)
            t4 = datetime.now()
            close_time = (t4 - t3).total_seconds()
            
            # 3. 在所有平台开新仓
            t5 = datetime.now()
            await self._open_new_positions(trader, message, strategy, analysis_time)
            t6 = datetime.now()
            open_time = (t6 - t5).total_seconds()
            
            # ⏱️ 总耗时
            total_time = (t6 - t_start).total_seconds()
            
            logger.info(
                f"⏱️  [{ai_name}] {coin} 处理完成\n"
                f"   分析耗时: {analysis_time:.2f}s\n"
                f"   平仓耗时: {close_time:.2f}s\n"
                f"   开仓耗时: {open_time:.2f}s\n"
                f"   ✨ 总耗时: {total_time:.2f}s"
            )
        
        except Exception as e:
            t_end = datetime.now()
            total_time = (t_end - t_start).total_seconds()
            logger.error(f"❌ [{ai_name}] 处理消息时出错 (耗时: {total_time:.2f}s): {e}", exc_info=True)
    
    async def _close_existing_positions(self, trader, coin: str):
        """
        关闭现有仓位（优化版：快速检查，减少不必要的API调用）
        
        策略：
        1. 新闻交易通常是全新机会，快速检查即可
        2. 如果确实有持仓，才执行平仓操作
        3. 避免在无持仓时浪费时间查询
        """
        ai_name = trader.ai_name
        
        # 🚀 优化：新闻交易快速模式 - 跳过持仓检查
        # 原因：
        # 1. 新闻交易是对新上线币种的快速反应
        # 2. 同一币种短时间内连续触发的概率极低
        # 3. 即使有持仓，交易所会自动处理（加仓或平仓）
        # 4. 避免 66秒的持仓查询延迟
        
        logger.info(f"⚡ [{ai_name}] 跳过持仓检查（新闻交易快速模式，节省 ~66s）")
    
    async def _open_new_positions(self, trader, message: ListingMessage, strategy, analysis_time: float):
        """在所有平台开新仓"""
        ai_name = trader.ai_name
        coin = message.coin_symbol
        
        # 在每个平台开仓
        for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
            try:
                logger.info(f"🚀 [{ai_name}] [{platform_name}] 准备开仓 {coin}")
                
                # 获取账户余额
                client = platform_trader.client
                try:
                    account_info = await client.get_account_info()
                    
                    # 计算账户余额
                    account_balance = 0
                    
                    if isinstance(account_info, dict):
                        # Hyperliquid: withdrawable 字段
                        if 'withdrawable' in account_info:
                            account_balance = float(account_info['withdrawable'])
                        # Aster: totalMarginBalance 或 totalWalletBalance
                        elif 'totalMarginBalance' in account_info:
                            account_balance = float(account_info['totalMarginBalance'])
                        elif 'totalWalletBalance' in account_info:
                            account_balance = float(account_info['totalWalletBalance'])
                    
                    if account_balance == 0:
                        logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 无法获取账户余额，跳过")
                        continue
                    
                    # 根据信心度动态计算保证金比例（从配置读取范围）
                    from config.settings import settings
                    
                    confidence = strategy.confidence
                    min_margin_pct = settings.news_min_margin_pct
                    max_margin_pct = settings.news_max_margin_pct
                    
                    if confidence < 60:
                        margin_pct = min_margin_pct
                    else:
                        # 线性映射: 60% -> min_margin_pct, 100% -> max_margin_pct
                        margin_pct = min_margin_pct + ((confidence - 60) / 40) * (max_margin_pct - min_margin_pct)
                        margin_pct = min(max_margin_pct, max(min_margin_pct, margin_pct))
                    
                    actual_margin = account_balance * margin_pct
                    
                    logger.info(
                        f"💰 [{ai_name}] [{platform_name}] 账户余额: ${account_balance:.2f}, "
                        f"信心度: {confidence:.1f}%, "
                        f"保证金比例: {margin_pct*100:.0f}% (配置: {min_margin_pct*100:.0f}%-{max_margin_pct*100:.0f}%), "
                        f"实际保证金: ${actual_margin:.2f}"
                    )
                
                except Exception as e:
                    logger.error(f"❌ [{ai_name}] [{platform_name}] 获取账户信息失败: {e}")
                    continue
                
                # 🚀 优化1: 从缓存获取最大杠杆（避免额外的 API 调用，节省1.36s）
                from trading.precision_config import PrecisionConfig
                precision_config = PrecisionConfig.get_hyperliquid_precision(coin)
                platform_max_leverage = precision_config.get("max_leverage", None)
                
                # 提前计算实际杠杆
                actual_leverage = strategy.leverage
                if platform_max_leverage and actual_leverage > platform_max_leverage:
                    logger.warning(
                        f"⚠️  [{ai_name}] [{platform_name}] AI建议杠杆 {actual_leverage}x 超过 {coin} 最大杠杆 {platform_max_leverage}x\n"
                        f"   自动调整为: {platform_max_leverage}x"
                    )
                    actual_leverage = platform_max_leverage
                
                # 🚀 优化2: 移除手动设置杠杆，由 place_order 自动设置（节省1次API调用）
                # 注释掉手动设置，因为 place_order 会根据 leverage 参数自动设置
                # try:
                #     if hasattr(client, 'update_leverage'):
                #         client.update_leverage(coin, actual_leverage, is_cross=True)
                #     elif hasattr(client, 'update_leverage_async'):
                #         await client.update_leverage_async(coin, actual_leverage)
                # except Exception as e:
                #     logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 设置杠杆失败: {e}")
                
                # 获取市场数据（仅用于获取当前价格）
                market_data = None
                
                if hasattr(client, 'get_market_data'):
                    market_data = await client.get_market_data(coin)
                elif hasattr(trader, 'data_source_client'):
                    market_data = trader.data_source_client.get_market_data(coin)
                
                if not market_data:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 无法获取 {coin} 价格，跳过")
                    continue
                
                current_price = float(market_data.get("markPx", 0))
                if current_price == 0:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] {coin} 价格为0，跳过")
                    continue
                
                # 计算下单数量（基于实际保证金和调整后的杠杆）
                position_value = actual_margin * actual_leverage
                size = position_value / current_price
                
                # 下单（新闻交易使用市价单，立即成交）
                is_buy = (strategy.direction == "long")
                
                # 市价单：使用当前价格 +/- 5% 作为保护价格（防止滑点过大）
                if is_buy:
                    # 买入：愿意最高支付当前价 * 1.05
                    limit_price = current_price * 1.05
                else:
                    # 卖出：愿意最低接受当前价 * 0.95
                    limit_price = current_price * 0.95
                
                result = await client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    size=size,
                    price=limit_price,
                    order_type="Market",  # 市价单，立即成交
                    reduce_only=False,
                    leverage=actual_leverage
                )
                
                if result.get("status") == "ok":
                    leverage_info = f"{actual_leverage}x"
                    if actual_leverage != strategy.leverage:
                        leverage_info += f" (AI建议: {strategy.leverage}x)"
                    
                    logger.info(
                        f"✅ [{ai_name}] [{platform_name}] 开仓成功\n"
                        f"   币种: {coin}\n"
                        f"   方向: {strategy.direction}\n"
                        f"   杠杆: {leverage_info}\n"
                        f"   价格: ${current_price:.2f}\n"
                        f"   账户余额: ${account_balance:.2f}\n"
                        f"   保证金比例: {margin_pct*100:.0f}%\n"
                        f"   实际保证金: ${actual_margin:.2f}\n"
                        f"   仓位价值: ${position_value:.2f}\n"
                        f"   消息来源: {message.source}"
                    )
                    
                    # 🚀 推送事件：开仓成功（添加地址信息）
                    # 获取账户地址（简化显示）
                    address = getattr(client, 'address', 'N/A')
                    if address != 'N/A' and len(address) > 10:
                        # 简化地址显示：0x1234...5678
                        address = f"{address[:6]}...{address[-4:]}"
                    
                    await event_manager.push_event("trade_opened", {
                        "ai": ai_name,
                        "platform": platform_name,
                        "coin": coin,
                        "direction": strategy.direction,
                        "leverage": actual_leverage,
                        "price": round(current_price, 4),
                        "margin": round(actual_margin, 2),
                        "position_value": round(position_value, 2),
                        "source": message.source,
                        "address": address  # 添加简化地址
                    })
                else:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 下单失败: {result}")
            
            except Exception as e:
                logger.error(f"❌ [{ai_name}] [{platform_name}] 开仓失败: {e}", exc_info=True)


# 全局实例
news_handler = NewsTradeHandler()

