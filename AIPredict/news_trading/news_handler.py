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

logger = logging.getLogger(__name__)


class NewsTradeHandler:
    """消息交易处理器 - 使用现有独立AI账户"""
    
    def __init__(self):
        """初始化处理器"""
        self.individual_traders = []  # 将由外部设置
        self.configured_ais = []  # 配置的AI列表
        self.analyzers = {}  # AI分析器缓存
        
        logger.info("🚀 消息交易处理器初始化")
    
    def setup(self, individual_traders: List, configured_ais: List[str], ai_api_keys: dict):
        """
        配置处理器
        
        Args:
            individual_traders: Arena的独立AI交易者列表
            configured_ais: 配置的AI名称列表（如 ['claude', 'gpt', 'deepseek']）
            ai_api_keys: AI的API密钥字典
        """
        self.individual_traders = individual_traders
        self.configured_ais = [ai.lower() for ai in configured_ais]
        
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
        logger.info(f"📬 [消息交易] 收到上币消息: {coin} (来源: {message.source})")
        logger.info(f"🤖 准备让 {len(self.analyzers)} 个AI分析...")
        
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
            
            # 2. 检查并平掉现有仓位
            t3 = datetime.now()
            await self._close_existing_positions(trader, coin)
            t4 = datetime.now()
            close_time = (t4 - t3).total_seconds()
            
            # 3. 在所有平台开新仓
            t5 = datetime.now()
            await self._open_new_positions(trader, message, strategy)
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
        """关闭现有仓位（从交易所查询实际持仓，而非依赖本地记录）"""
        ai_name = trader.ai_name
        
        # 检查所有平台的持仓
        for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
            try:
                client = platform_trader.client
                
                # 🔑 关键：从交易所查询实际持仓，而非依赖本地记录
                logger.info(f"🔍 [{ai_name}] [{platform_name}] 查询 {coin} 实际持仓...")
                account_info = await client.get_account_info()
                
                has_position = False
                actual_size = 0
                actual_side = None
                
                # 检查交易所是否有该币种的实际持仓
                for asset_pos in account_info.get('assetPositions', []):
                    if asset_pos['position']['coin'] == coin:
                        szi = float(asset_pos['position']['szi'])
                        actual_size = abs(szi)
                        actual_side = 'long' if szi > 0 else 'short'
                        has_position = True
                        break
                
                if has_position:
                    logger.info(
                        f"📤 [{ai_name}] [{platform_name}] 检测到 {coin} 实际持仓\n"
                        f"   方向: {actual_side}\n"
                        f"   数量: {actual_size}\n"
                        f"   准备平仓..."
                    )
                    
                    # 平仓
                    await platform_trader.close_position(coin, "消息触发平仓")
                    
                    logger.info(f"✅ [{ai_name}] [{platform_name}] {coin} 平仓完成")
                    
                    # 同步本地记录：如果本地没有记录但交易所有持仓，清理差异
                    if coin not in platform_trader.positions:
                        logger.warning(
                            f"⚠️  [{ai_name}] [{platform_name}] 本地无 {coin} 记录，但交易所有持仓\n"
                            f"   已平仓，本地与交易所已同步"
                        )
                else:
                    logger.info(f"ℹ️  [{ai_name}] [{platform_name}] 交易所无 {coin} 持仓")
                    
                    # 如果本地有记录但交易所没有，清除本地记录
                    if coin in platform_trader.positions:
                        logger.warning(
                            f"⚠️  [{ai_name}] [{platform_name}] 本地有 {coin} 记录，但交易所无持仓\n"
                            f"   清除本地无效记录"
                        )
                        del platform_trader.positions[coin]
                        
            except Exception as e:
                logger.error(f"❌ [{ai_name}] [{platform_name}] 查询/平仓失败: {e}")
    
    async def _open_new_positions(self, trader, message: ListingMessage, strategy):
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
                    if hasattr(account_info, 'get'):
                        # Aster返回字典
                        if 'totalMarginBalance' in account_info:
                            account_balance = float(account_info.get('totalMarginBalance', 0))
                        elif 'totalWalletBalance' in account_info:
                            account_balance = float(account_info.get('totalWalletBalance', 0))
                        else:
                            account_balance = 0
                    else:
                        # Hyperliquid可能返回对象
                        account_balance = getattr(account_info, 'withdrawable', 0)
                    
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
                
                # 获取价格
                market_data = None
                
                if hasattr(client, 'get_market_data'):
                    market_data = client.get_market_data(coin)
                elif hasattr(trader, 'data_source_client'):
                    market_data = trader.data_source_client.get_market_data(coin)
                
                if not market_data:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 无法获取 {coin} 价格，跳过")
                    continue
                
                current_price = float(market_data.get("markPx", 0))
                if current_price == 0:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] {coin} 价格为0，跳过")
                    continue
                
                # 设置杠杆
                try:
                    if hasattr(client, 'update_leverage'):
                        client.update_leverage(coin, strategy.leverage, is_cross=True)
                    elif hasattr(client, 'update_leverage_async'):
                        await client.update_leverage_async(coin, strategy.leverage)
                except Exception as e:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 设置杠杆失败: {e}")
                
                # 计算下单数量（基于实际保证金）
                position_value = actual_margin * strategy.leverage
                size = position_value / current_price
                
                # 下单
                is_buy = (strategy.direction == "long")
                
                result = await client.place_order(
                    coin=coin,
                    is_buy=is_buy,
                    sz=size,
                    limit_px=current_price * (1.01 if is_buy else 0.99),
                    reduce_only=False,
                    leverage=strategy.leverage
                )
                
                if result.get("status") == "ok":
                    logger.info(
                        f"✅ [{ai_name}] [{platform_name}] 开仓成功\n"
                        f"   币种: {coin}\n"
                        f"   方向: {strategy.direction}\n"
                        f"   杠杆: {strategy.leverage}x\n"
                        f"   价格: ${current_price:.2f}\n"
                        f"   账户余额: ${account_balance:.2f}\n"
                        f"   仓位比例: {position_size_pct*100:.0f}%\n"
                        f"   实际保证金: ${actual_margin:.2f}\n"
                        f"   仓位价值: ${position_value:.2f}\n"
                        f"   消息来源: {message.source}"
                    )
                else:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 下单失败: {result}")
            
            except Exception as e:
                logger.error(f"❌ [{ai_name}] [{platform_name}] 开仓失败: {e}", exc_info=True)


# 全局实例
news_handler = NewsTradeHandler()

