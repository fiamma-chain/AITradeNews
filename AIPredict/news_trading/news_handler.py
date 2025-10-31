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
    """消息交易处理器 - 使用 Alpha Hunter 注册的 Agent 账户"""
    
    def __init__(self):
        """初始化处理器"""
        self.alpha_hunter = None  # Alpha Hunter 实例（将由外部设置）
        self.configured_ais = []  # 配置的AI列表
        self.analyzers = {}  # AI分析器缓存 {ai_name: NewsAnalyzer}
        self.recent_messages = {}  # 最近处理的消息 {coin: timestamp}
        self.message_cooldown = 60  # 消息冷却时间（秒），同一币种60秒内只处理一次
        
        logger.info("🚀 消息交易处理器初始化")
    
    def setup(self, alpha_hunter, active_ais: List[str], ai_api_keys: dict, monitored_coins: List[str] = None):
        """
        配置处理器
        
        Args:
            alpha_hunter: AlphaHunter 实例
            active_ais: 激活的AI名称列表（如 ['grok', 'claude']）
            ai_api_keys: AI的API密钥字典
            monitored_coins: 监控的币种列表（如 ['ASTER']），如果为None则监控所有
        """
        self.alpha_hunter = alpha_hunter
        self.configured_ais = [ai.lower() for ai in active_ais]
        self.monitored_coins = [coin.upper() for coin in monitored_coins] if monitored_coins else None
        
        # 为每个激活的AI创建分析器
        for ai_name in self.configured_ais:
            api_key = ai_api_keys.get(ai_name)
            if not api_key:
                logger.warning(f"⚠️  {ai_name} 没有API Key，跳过")
                continue
            
            analyzer = create_news_analyzer(ai_name, api_key)
            if analyzer:
                self.analyzers[ai_name] = analyzer
                logger.info(f"✅ 已为 {ai_name} 创建分析器")
        
        logger.info(f"📊 消息交易已配置，激活的AI: {list(self.analyzers.keys())}")
    
    async def handle_message(self, message: ListingMessage):
        """
        处理上币消息 - 所有配置的AI并发分析和交易
        
        Args:
            message: 上币消息
        """
        coin = message.coin_symbol
        
        # 🔥 动态获取监控币种：从 Alpha Hunter 获取所有活跃用户的监控币种
        active_monitored_coins = []
        if self.alpha_hunter:
            active_monitored_coins = [c.upper() for c in self.alpha_hunter.get_all_active_coins()]
        
        # 过滤：只处理监控的币种（如果有活跃用户）
        if active_monitored_coins and coin.upper() not in active_monitored_coins:
            logger.info(f"⏭️  [消息交易] 跳过未监控的币种: {coin} (当前监控列表: {active_monitored_coins})")
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
        
        # 🚀 AI 决策共享优化：每个 AI 只分析一次，所有用户共享决策结果
        if not self.alpha_hunter or not self.alpha_hunter.configs:
            logger.warning(f"⚠️  没有注册的用户，跳过交易")
            return
        
        # 找出所有监控这个币种的用户
        interested_users = []
        for user_address, user_config in self.alpha_hunter.configs.items():
            if coin.upper() in [c.upper() for c in user_config.monitored_coins]:
                interested_users.append((user_address, user_config))
        
        if not interested_users:
            logger.info(f"⏭️  没有用户监控 {coin}，跳过")
            return
        
        logger.info(f"📊 {len(interested_users)} 个用户监控 {coin}，{len(self.analyzers)} 个AI将分析")
        
        # 为每个激活的 AI 创建分析任务（只分析一次）
        ai_analysis_tasks = []
        for ai_name in self.analyzers.keys():
            task = self._analyze_and_execute_for_all_users(ai_name, message, interested_users)
            ai_analysis_tasks.append(task)
        
        # 并发执行所有 AI 的分析和交易
        logger.info(f"🚀 开始执行 {len(ai_analysis_tasks)} 个AI分析任务")
        await asyncio.gather(*ai_analysis_tasks, return_exceptions=True)
    
    async def _analyze_and_execute_for_all_users(self, ai_name: str, message: ListingMessage, interested_users: list):
        """
        🚀 AI 决策共享：一次分析，多用户执行
        
        Args:
            ai_name: AI 名称
            message: 上币消息
            interested_users: 监控该币种的用户列表 [(user_address, user_config), ...]
        """
        coin = message.coin_symbol
        analyzer = self.analyzers.get(ai_name)
        
        if not analyzer:
            logger.warning(f"⚠️  [{ai_name}] 分析器不存在")
            return
        
        try:
            # ⭐ 第一步：调用 AI 分析（只调用一次）
            logger.info(f"🤖 [{ai_name}] 开始分析 {coin}...")
            t1 = datetime.now()
            strategy = await analyzer.analyze(message)
            t2 = datetime.now()
            
            analysis_time = (t2 - t1).total_seconds()
            logger.info(f"✅ [{ai_name}] 分析完成 ({analysis_time:.2f}s)")
            
            if not strategy or not strategy.should_trade:
                logger.info(f"⏭️  [{ai_name}] 决定不交易 {coin}")
                
                # 推送事件：AI 决定不交易
                await event_manager.push_event("ai_decision", {
                    "ai_name": ai_name,
                    "coin": coin,
                    "decision": "skip",
                    "reasoning": strategy.reasoning if strategy else "No strategy",
                    "analysis_time": analysis_time
                })
                return
            
            logger.info(
                f"📊 [{ai_name}] 交易策略:\n"
                f"   方向: {strategy.direction}\n"
                f"   杠杆: {strategy.leverage}x\n"
                f"   信心度: {strategy.confidence}%"
            )
            
            # 推送事件：AI 决策完成
            await event_manager.push_event("ai_decision", {
                "ai_name": ai_name,
                "coin": coin,
                "decision": strategy.direction,
                "leverage": strategy.leverage,
                "confidence": strategy.confidence,
                "reasoning": strategy.reasoning,
                "analysis_time": analysis_time
            })
            
            # ⭐ 第二步：为所有监控该币种的用户并发执行交易
            logger.info(f"🚀 [{ai_name}] 为 {len(interested_users)} 个用户执行交易...")
            
            execution_tasks = []
            for user_address, user_config in interested_users:
                agent_client = self.alpha_hunter.agent_clients.get(user_address)
                if not agent_client:
                    logger.warning(f"⚠️  用户 {user_address[:10]}... 的 Agent 客户端不存在")
                    continue
                
                # 获取该币种的保证金
                margin = user_config.margin_per_coin.get(coin.upper())
                if margin is None:
                    margin = user_config.margin_per_coin.get(coin)
                
                if margin is None:
                    logger.warning(f"⚠️  用户 {user_address[:10]}... 未配置 {coin} 的保证金")
                    continue
                
                # 创建执行任务
                task = self._execute_trade(
                    agent_client=agent_client,
                    user_config=user_config,
                    ai_name=ai_name,
                    user_address=user_address,
                    message=message,
                    strategy=strategy,
                    analysis_time=analysis_time
                )
                execution_tasks.append(task)
            
            # 并发执行所有用户的交易
            if execution_tasks:
                await asyncio.gather(*execution_tasks, return_exceptions=True)
                logger.info(f"✅ [{ai_name}] 所有用户交易执行完成")
            
        except Exception as e:
            logger.error(f"❌ [{ai_name}] 分析或执行失败: {e}", exc_info=True)
    
    async def _handle_single_ai(self, user_address: str, user_config, ai_name: str, message: ListingMessage):
        """单个AI为单个用户处理消息（已废弃，保留用于向后兼容）"""
        coin = message.coin_symbol
        analyzer = self.analyzers.get(ai_name)
        
        # 获取用户的 Agent 客户端
        agent_client = self.alpha_hunter.agent_clients.get(user_address)
        
        if not analyzer or not agent_client:
            if not analyzer:
                logger.warning(f"⚠️  [{ai_name}] 分析器不存在")
            if not agent_client:
                logger.warning(f"⚠️  用户 {user_address[:10]}... 的 Agent 客户端不存在")
            return
        
        user_short = user_address[:6] + "..." + user_address[-4:]
        
        # 🕐 开始计时
        t_start = datetime.now()
        
        try:
            logger.info(f"🤖 [{ai_name}] 为用户 {user_short} 分析 {coin}")
            
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
                "analysis_time": round(analysis_time, 2),
                "user": user_short
            })
            
            # 2. 开仓交易（使用 Agent 客户端）
            t3 = datetime.now()
            await self._execute_trade(agent_client, user_config, ai_name, user_address, message, strategy, analysis_time)
            t4 = datetime.now()
            trade_time = (t4 - t3).total_seconds()
            
            # ⏱️ 总耗时
            total_time = (t4 - t_start).total_seconds()
            
            logger.info(
                f"⏱️  [{ai_name}] {coin} 处理完成 (用户: {user_short})\n"
                f"   分析耗时: {analysis_time:.2f}s\n"
                f"   交易耗时: {trade_time:.2f}s\n"
                f"   ✨ 总耗时: {total_time:.2f}s"
            )
        
        except Exception as e:
            t_end = datetime.now()
            total_time = (t_end - t_start).total_seconds()
            logger.error(f"❌ [{ai_name}] 处理消息时出错 (耗时: {total_time:.2f}s): {e}", exc_info=True)
    
    async def _execute_trade(self, agent_client, user_config, ai_name: str, user_address: str, message: ListingMessage, strategy, analysis_time: float):
        """
        使用 Agent 客户端执行交易
        
        Args:
            agent_client: 用户的 Agent HyperliquidClient
            user_config: 用户配置（AlphaHunterConfig）
            ai_name: AI 名称
            user_address: 用户地址
            message: 上币消息
            strategy: AI 分析的交易策略
            analysis_time: AI 分析耗时
        """
        coin = message.coin_symbol
        user_short = user_address[:6] + "..." + user_address[-4:]
        
        try:
            logger.info(f"🚀 [{ai_name}] 为用户 {user_short} 准备在 Hyperliquid 开仓 {coin}")
            
            # 1. 获取账户余额
            account_info = await agent_client.get_account_info()
            account_balance = float(account_info.get('withdrawable', 0))
            
            if account_balance == 0:
                logger.warning(f"⚠️  [{ai_name}] 用户 {user_short} 账户余额为0，跳过")
                return
            
            # 2. 检查用户是否为该币种配置了保证金
            if coin not in user_config.margin_per_coin:
                logger.info(f"⏭️  [{ai_name}] 用户 {user_short} 未配置 {coin} 的保证金，跳过交易")
                return
            
            # 3. 计算保证金（使用用户输入的金额作为最大保证金）
            user_max_margin = user_config.margin_per_coin[coin]
            actual_margin = min(user_max_margin, account_balance)
            
            if actual_margin < user_max_margin:
                logger.warning(
                    f"⚠️  [{ai_name}] 用户 {user_short} 账户余额不足\n"
                    f"   用户输入金额: ${user_max_margin:.2f}\n"
                    f"   账户余额: ${account_balance:.2f}\n"
                    f"   实际使用: ${actual_margin:.2f}"
                )
            else:
                logger.info(
                    f"💰 [{ai_name}] 用户 {user_short} 保证金配置\n"
                    f"   用户输入金额: ${user_max_margin:.2f}\n"
                    f"   账户余额: ${account_balance:.2f}\n"
                    f"   实际使用: ${actual_margin:.2f} (已限制为用户输入金额)"
                )
            
            # 4. 获取并验证最大杠杆
            from trading.precision_config import PrecisionConfig
            precision_config = PrecisionConfig.get_hyperliquid_precision(coin)
            platform_max_leverage = precision_config.get("max_leverage", 50)
            
            actual_leverage = min(strategy.leverage, platform_max_leverage)
            if actual_leverage != strategy.leverage:
                logger.warning(
                    f"⚠️  [{ai_name}] AI建议杠杆 {strategy.leverage}x 超过 {coin} 最大杠杆 {platform_max_leverage}x\n"
                    f"   自动调整为: {actual_leverage}x"
                )
            
            # 5. 获取当前价格
            market_data = await agent_client.get_market_data(coin)
            current_price = float(market_data.get("markPx", 0))
            
            if current_price == 0:
                logger.warning(f"⚠️  [{ai_name}] {coin} 价格为0，跳过")
                return
            
            # 6. 计算下单数量
            position_value = actual_margin * actual_leverage
            size = position_value / current_price
            
            # 7. 下单（市价单，5%价格保护）
            is_buy = (strategy.direction.lower() == "long")
            protection = 0.05
            limit_price = current_price * (1 + protection if is_buy else 1 - protection)
            
            logger.info(
                f"📝 [{ai_name}] 下单参数:\n"
                f"   方向: {'BUY (LONG)' if is_buy else 'SELL (SHORT)'}\n"
                f"   数量: {size:.4f}\n"
                f"   价格: ${current_price:.4f} (限价保护: ${limit_price:.4f})\n"
                f"   杠杆: {actual_leverage}x\n"
                f"   保证金: ${actual_margin:.2f}"
            )
            
            result = await agent_client.place_order(
                coin=coin,
                is_buy=is_buy,
                size=size,
                price=limit_price,
                leverage=actual_leverage,
                reduce_only=False
            )
            
            logger.info(f"✅ [{ai_name}] 订单成功: {result}")
            
            # 8. 推送事件：交易开仓成功
            await event_manager.push_event("trade_opened", {
                "ai": ai_name,
                "coin": coin,
                "direction": strategy.direction,
                "price": current_price,
                "size": size,
                "leverage": actual_leverage,
                "margin": actual_margin,
                "address": user_short,
                "user_address": user_address
            })
            
        except Exception as e:
            logger.error(f"❌ [{ai_name}] 交易执行失败: {e}", exc_info=True)


# 全局实例
news_handler = NewsTradeHandler()

# 旧方法已删除（不再使用 individual_traders，改用 Alpha Hunter 的 Agent 客户端）
