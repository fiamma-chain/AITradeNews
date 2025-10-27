"""
消息驱动交易处理器 - DEX扩展版
News Trading Handler with DEX Support

支持CEX（Hyperliquid/Aster）和DEX（Uniswap/PancakeSwap）
"""
import logging
from datetime import datetime
from typing import Optional, Dict
from decimal import Decimal

from .message_listeners.base_listener import ListingMessage
from trading.client_factory import client_factory
from trading.dex import is_dex_token, get_token_chain
from config.settings import settings

logger = logging.getLogger(__name__)


class DEXNewsTradeHandler:
    """消息交易处理器 - 支持DEX"""
    
    def __init__(self):
        """初始化处理器"""
        self.individual_traders = []
        self.configured_ais = []
        self.analyzers = {}
        
        logger.info("🚀 消息交易处理器初始化（支持DEX）")
    
    def setup(self, individual_traders: list, configured_ais: list, ai_api_keys: dict):
        """配置处理器"""
        from .news_analyzer import create_news_analyzer
        
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
            
            try:
                analyzer = create_news_analyzer(ai_name_lower, api_key)
                self.analyzers[ai_name_lower] = analyzer
                logger.info(f"✅ [{trader.ai_name}] 分析器已创建")
            except Exception as e:
                logger.error(f"❌ [{trader.ai_name}] 创建分析器失败: {e}")
        
        logger.info(f"🎯 消息交易配置完成，启用AI: {list(self.analyzers.keys())}")
    
    async def handle_message(self, message: ListingMessage):
        """处理消息 - 所有配置的AI独立分析和交易"""
        coin = message.coin_symbol
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📨 收到消息: {coin} @ {message.source}")
        logger.info(f"{'='*60}")
        
        # 检查代币类型
        if is_dex_token(coin):
            chain = get_token_chain(coin)
            logger.info(f"🔍 DEX代币检测: {coin} on {chain.upper()}")
        else:
            logger.info(f"🔍 CEX代币检测: {coin}")
        
        # 为每个配置的AI创建独立任务
        import asyncio
        tasks = []
        
        for trader in self.individual_traders:
            ai_name_lower = trader.ai_name.lower()
            
            if ai_name_lower not in self.analyzers:
                continue
            
            task = asyncio.create_task(
                self._process_single_ai(trader, message, ai_name_lower)
            )
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.warning(f"⚠️  没有可用的AI处理消息: {coin}")
    
    async def _process_single_ai(self, trader, message: ListingMessage, ai_name_lower: str):
        """单个AI的完整处理流程"""
        ai_name = trader.ai_name
        coin = message.coin_symbol
        t_start = datetime.now()
        
        try:
            # 1. AI分析
            logger.info(f"🤖 [{ai_name}] 开始分析 {coin}...")
            t1 = datetime.now()
            
            analyzer = self.analyzers[ai_name_lower]
            strategy = await analyzer.analyze_listing_message(message)
            
            t2 = datetime.now()
            analysis_time = (t2 - t1).total_seconds()
            
            if not strategy or not strategy.should_trade:
                logger.info(f"❌ [{ai_name}] {coin} 不满足交易条件")
                return
            
            logger.info(
                f"✅ [{ai_name}] {coin} 分析完成 ({analysis_time:.2f}s)\n"
                f"   方向: {strategy.direction}\n"
                f"   杠杆: {strategy.leverage}x\n"
                f"   信心度: {strategy.confidence:.1f}%"
            )
            
            # 2. 检查是否为DEX代币
            if is_dex_token(coin):
                # DEX交易流程
                await self._handle_dex_trade(trader, message, strategy, ai_name)
            else:
                # CEX交易流程（使用现有逻辑）
                await self._handle_cex_trade(trader, message, strategy, ai_name)
            
            t_end = datetime.now()
            total_time = (t_end - t_start).total_seconds()
            logger.info(f"⏱️  [{ai_name}] {coin} 总耗时: {total_time:.2f}s")
        
        except Exception as e:
            t_end = datetime.now()
            total_time = (t_end - t_start).total_seconds()
            logger.error(f"❌ [{ai_name}] 处理消息时出错 (耗时: {total_time:.2f}s): {e}", exc_info=True)
    
    async def _handle_dex_trade(self, trader, message: ListingMessage, strategy, ai_name: str):
        """处理DEX交易"""
        coin = message.coin_symbol
        
        logger.info(f"🦄 [{ai_name}] DEX交易流程开始: {coin}")
        
        try:
            # 创建DEX客户端
            dex_client = client_factory.create_client(coin, private_key=None)
            
            if not dex_client:
                logger.error(f"❌ [{ai_name}] 无法创建DEX客户端for {coin}")
                return
            
            # 获取账户信息
            account_info = await dex_client.get_account_info()
            account_balance = account_info.get('withdrawable', 0)
            
            if account_balance < 10:
                logger.warning(f"⚠️  [{ai_name}] DEX账户余额不足: ${account_balance:.2f}")
                return
            
            logger.info(f"💰 [{ai_name}] DEX账户余额: ${account_balance:.2f}")
            
            # 计算交易金额（DEX现货，无杠杆）
            # 根据信心度使用10%-50%的余额
            confidence = strategy.confidence
            if confidence < 60:
                amount_pct = 0.10
            else:
                # 60% -> 10%, 100% -> 50%
                amount_pct = 0.10 + ((confidence - 60) / 40) * 0.40
            
            trade_amount = account_balance * amount_pct
            
            logger.info(
                f"📊 [{ai_name}] DEX交易计算:\n"
                f"   信心度: {confidence:.1f}%\n"
                f"   使用比例: {amount_pct*100:.0f}%\n"
                f"   交易金额: ${trade_amount:.2f}"
            )
            
            # 执行交易
            is_buy = (strategy.direction == "long")
            
            logger.info(f"🚀 [{ai_name}] 执行DEX交易: {'买入' if is_buy else '卖出'} {coin}")
            
            result = await dex_client.place_order(
                coin=coin,
                is_buy=is_buy,
                sz=trade_amount,
            )
            
            if result.get("status") == "ok":
                logger.info(
                    f"✅ [{ai_name}] DEX交易成功\n"
                    f"   交易哈希: {result.get('tx_hash')}\n"
                    f"   Gas消耗: {result.get('gas_used')}"
                )
            else:
                logger.error(f"❌ [{ai_name}] DEX交易失败: {result.get('message')}")
        
        except Exception as e:
            logger.error(f"❌ [{ai_name}] DEX交易异常: {e}", exc_info=True)
    
    async def _handle_cex_trade(self, trader, message: ListingMessage, strategy, ai_name: str):
        """处理CEX交易（复用现有逻辑）"""
        coin = message.coin_symbol
        
        logger.info(f"🏦 [{ai_name}] CEX交易流程开始: {coin}")
        
        # 1. 平仓现有持仓
        await self._close_existing_positions(trader, coin, ai_name)
        
        # 2. 开新仓
        await self._open_new_positions(trader, message, strategy, ai_name)
    
    async def _close_existing_positions(self, trader, coin: str, ai_name: str):
        """关闭现有仓位"""
        for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
            try:
                if coin in platform_trader.positions:
                    logger.info(f"📤 [{ai_name}] [{platform_name}] 存在 {coin} 仓位，先平仓")
                    await platform_trader.close_position(coin, "消息触发平仓")
                    logger.info(f"✅ [{ai_name}] [{platform_name}] {coin} 平仓完成")
            except Exception as e:
                logger.error(f"❌ [{ai_name}] [{platform_name}] 平仓失败: {e}")
    
    async def _open_new_positions(self, trader, message: ListingMessage, strategy, ai_name: str):
        """在所有CEX平台开新仓"""
        coin = message.coin_symbol
        
        for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
            try:
                logger.info(f"🚀 [{ai_name}] [{platform_name}] 准备开仓 {coin}")
                
                client = platform_trader.client
                account_info = await client.get_account_info()
                
                # 计算账户余额
                if hasattr(account_info, 'get'):
                    if 'totalMarginBalance' in account_info:
                        account_balance = float(account_info.get('totalMarginBalance', 0))
                    elif 'totalWalletBalance' in account_info:
                        account_balance = float(account_info.get('totalWalletBalance', 0))
                    else:
                        account_balance = 0
                else:
                    account_balance = getattr(account_info, 'withdrawable', 0)
                
                if account_balance == 0:
                    logger.warning(f"⚠️  [{ai_name}] [{platform_name}] 无法获取账户余额，跳过")
                    continue
                
                # 根据信心度动态计算保证金比例
                confidence = strategy.confidence
                min_margin_pct = settings.news_min_margin_pct
                max_margin_pct = settings.news_max_margin_pct
                
                if confidence < 60:
                    margin_pct = min_margin_pct
                else:
                    margin_pct = min_margin_pct + ((confidence - 60) / 40) * (max_margin_pct - min_margin_pct)
                    margin_pct = min(max_margin_pct, max(min_margin_pct, margin_pct))
                
                actual_margin = account_balance * margin_pct
                
                logger.info(
                    f"💰 [{ai_name}] [{platform_name}] 账户余额: ${account_balance:.2f}, "
                    f"信心度: {confidence:.1f}%, "
                    f"保证金比例: {margin_pct*100:.0f}%, "
                    f"实际保证金: ${actual_margin:.2f}"
                )
                
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
                
                # 计算下单数量
                position_value = actual_margin * strategy.leverage
                sz = position_value / current_price
                
                logger.info(
                    f"📊 [{ai_name}] [{platform_name}] 下单参数:\n"
                    f"   杠杆: {strategy.leverage}x\n"
                    f"   保证金: ${actual_margin:.2f}\n"
                    f"   仓位价值: ${position_value:.2f}\n"
                    f"   当前价格: ${current_price:.6f}\n"
                    f"   下单数量: {sz:.6f} {coin}"
                )
                
                # 下单
                is_buy = (strategy.direction == "long")
                result = await platform_trader.auto_trader.execute_trade(
                    coin=coin,
                    is_buy=is_buy,
                    sz=sz,
                    reduce_only=False
                )
                
                if result.get("status") == "ok":
                    logger.info(f"✅ [{ai_name}] [{platform_name}] {coin} 开仓成功")
                else:
                    logger.error(f"❌ [{ai_name}] [{platform_name}] {coin} 开仓失败: {result}")
            
            except Exception as e:
                logger.error(f"❌ [{ai_name}] [{platform_name}] 开仓异常: {e}", exc_info=True)


# 全局处理器实例
dex_news_handler = DEXNewsTradeHandler()

