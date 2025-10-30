"""
AI共识交易系统 - 多平台对比版
支持同时在 Hyperliquid 和 Aster 平台上交易，对比收益
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config.settings import settings, get_enabled_platforms, get_individual_traders_config
from ai_models.deepseek_trader import DeepSeekTrader
from ai_models.claude_trader import ClaudeTrader
from ai_models.grok_trader import GrokTrader
from ai_models.gpt_trader import GPTTrader
from ai_models.gemini_trader import GeminiTrader
from ai_models.qwen_trader import QwenTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.aster.client import AsterClient
from trading.multi_platform_trader import MultiPlatformTrader
from utils.symbol_filter import symbol_filter
from trading.kline_manager import KlineManager
from ai_models.base_ai import TradingDecision
from utils.redis_manager import redis_manager

# 消息驱动交易系统
from news_trading.news_handler import news_handler
from news_trading.url_scraper import scrape_url_content
from news_trading.message_listeners.binance_listing_listener import (
    create_binance_spot_listener,
    create_binance_futures_listener
)
from news_trading.message_listeners.binance_listener import create_binance_alpha_listener
from news_trading.message_listeners.upbit_listing_listener import create_upbit_listener
from news_trading.message_listeners.coinbase_listener import create_coinbase_listener
from news_trading.message_listeners.base_listener import ListingMessage
from news_trading.config import is_supported_coin
from config.settings import get_news_trading_ais

# Alpha Hunter 系统
from news_trading.alpha_hunter import alpha_hunter

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 静态文件路由 - 提供logo图片访问
from fastapi.staticfiles import StaticFiles
app.mount("/images", StaticFiles(directory="web/images"), name="images")

# 全局变量 - 消息监听器
news_listeners = []
news_listener_tasks = []


class IndividualAITrader:
    """独立AI交易者 - 单个AI独立决策和交易"""
    
    def __init__(self, name: str, ai_trader, private_key: str):
        """
        初始化独立AI交易者
        
        Args:
            name: 交易者名称
            ai_trader: AI交易者实例
            private_key: 私钥
        """
        self.name = name
        self.ai_trader = ai_trader
        self.ai_name = ai_trader.__class__.__name__.replace('Trader', '')
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()
        
        # 创建多平台交易管理器
        self.multi_trader = MultiPlatformTrader()
        
        # 🎯 独立AI交易者：只在 Hyperliquid 平台下单
        logger.info(f"[{name}] 独立AI交易者 - 仅在 Hyperliquid 平台交易")
        client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
        self.multi_trader.add_platform(client, f"{name}-Hyperliquid")
        
        # Hyperliquid 同时作为交易平台和数据源
        self.data_source_client = client
        
        # 保存用于获取市场数据的客户端
        if self.data_source_client:
            self.primary_client = self.data_source_client
        else:
            self.primary_client = list(self.multi_trader.platform_traders.values())[0].client if self.multi_trader.platform_traders else None
        
        # 统计数据
        self.stats = {
            "trader_name": name,
            "ai_name": self.ai_name,
            "type": "individual",
            "platforms": {},
            "decisions": [],
            "platform_comparison": {}
        }
    
    async def initialize(self):
        """初始化交易者"""
        # 独立AI交易者使用独立的初始余额配置（200 USDT）
        await self.multi_trader.initialize_all(settings.individual_ai_initial_balance, self.name)
        
        # 同步各平台持仓
        for platform_name, trader in self.multi_trader.platform_traders.items():
            await self._sync_existing_positions(trader)
    
    async def _sync_existing_positions(self, trader):
        """同步平台持仓"""
        try:
            logger.info(f"[{trader.name}] 🔄 正在同步现有持仓...")
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    trader.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': '系统启动时同步的历史持仓',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{trader.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{trader.name}] 解析持仓失败: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{trader.name}] ✅ 已同步 {synced_count} 个现有持仓")
            else:
                logger.info(f"[{trader.name}] 📭 没有现有持仓")
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ 同步持仓失败: {e}")
    
    async def get_decision(
        self, 
        coin: str, 
        market_data: Dict, 
        orderbook: Dict, 
        recent_trades: List,
        position_info: Optional[Dict] = None
    ) -> Tuple[Optional[TradingDecision], float, str]:
        """获取AI决策（无需共识）"""
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        try:
            logger.info(f"[{self.name}] 🤖 正在获取 {self.ai_name} 的决策...")
            
            # 注入K线数据
            original_create_prompt = self.ai_trader.create_market_prompt
            def wrapped_prompt(c, m, o, p=None, kline_history=None):
                return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
            self.ai_trader.create_market_prompt = wrapped_prompt
            
            decision, confidence, reasoning = await self.ai_trader.analyze_market(
                coin, market_data, orderbook, recent_trades, position_info
            )
            
            # 恢复原始方法
            self.ai_trader.create_market_prompt = original_create_prompt
            
            logger.info(f"[{self.name}]    {self.ai_name}: {decision} (信心: {confidence:.1f}%)")
            
            return decision, confidence, reasoning
        
        except Exception as e:
            logger.error(f"[{self.name}] ❌ {self.ai_name} 决策失败: {e}")
            return None, 0, f"决策失败: {str(e)}"
    
    async def execute_decision_on_all_platforms(
        self, 
        coin: str, 
        decision: TradingDecision, 
        confidence: float, 
        reasoning: str, 
        current_price: float
    ):
        """在所有平台上执行决策"""
        if decision == TradingDecision.HOLD:
            logger.debug(f"[{self.name}] 💤 AI 建议观望，不执行交易")
            return
        
        logger.info(f"[{self.name}] 🚀 在所有平台上执行决策: {decision}")
        results = await self.multi_trader.execute_decision_all(
            coin, decision, confidence, reasoning, current_price, self.name
        )
        
        for platform_name, result in results.items():
            if result:
                logger.info(f"[{platform_name}] ✅ 交易已执行")
            else:
                logger.info(f"[{platform_name}] ⚠️  交易未执行")
    
    async def update_stats(self):
        """更新统计数据"""
        await self.multi_trader.update_all_stats()
        
        # 更新统计
        comparison = self.multi_trader.get_comparison_stats()
        self.stats["platform_comparison"] = comparison
        
        # 为每个平台更新统计
        for platform_name, trader in self.multi_trader.platform_traders.items():
            self.stats["platforms"][platform_name] = trader.stats


class AIGroup:
    """AI组 - 多平台版本"""
    
    def __init__(self, name: str, ai_traders: List, private_key: str):
        """
        初始化 AI 组
        
        Args:
            name: 组名
            ai_traders: AI 交易者列表
            private_key: 私钥
        """
        self.name = name
        self.ai_traders = ai_traders
        self.kline_manager = KlineManager(max_klines=16)
        self.start_time = datetime.now()
        
        # 创建多平台交易管理器
        self.multi_trader = MultiPlatformTrader()
        
        # 🎯 AI共识组（Alpha/Beta）：在两个平台下单
        enabled_platforms = get_enabled_platforms()
        logger.info(f"[{name}] AI共识组 - 在以下平台交易: {enabled_platforms}")
        
        for platform in enabled_platforms:
            if platform == "hyperliquid":
                client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
                self.multi_trader.add_platform(client, f"{name}-Hyperliquid")
            elif platform == "aster":
                client = AsterClient(private_key, settings.aster_testnet)
                self.multi_trader.add_platform(client, f"{name}-Aster")
        
        # 创建用于获取市场数据的 Hyperliquid 客户端（即使不用于交易）
        # 这样可以保持使用 Hyperliquid 的深度数据，但不在其上交易
        if "hyperliquid" not in enabled_platforms:
            logger.info(f"[{name}] 📊 创建 Hyperliquid 数据源客户端（仅用于获取市场数据）")
            self.data_source_client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
        else:
            self.data_source_client = None
        
        # 保存用于获取市场数据的客户端
        if self.data_source_client:
            self.primary_client = self.data_source_client
        else:
            self.primary_client = list(self.multi_trader.platform_traders.values())[0].client if self.multi_trader.platform_traders else None
        
        # 统计数据
        self.stats = {
            "group_name": name,
            "platforms": {},
            "consensus_decisions": [],
            "platform_comparison": {}
        }
    
    async def initialize(self):
        """初始化组"""
        # 传入组名，用于从Redis恢复交易记录
        await self.multi_trader.initialize_all(settings.ai_initial_balance, self.name)
        
        # 同步各平台持仓
        for platform_name, trader in self.multi_trader.platform_traders.items():
            await self._sync_existing_positions(trader)
    
    async def _sync_existing_positions(self, trader):
        """同步平台持仓"""
        try:
            logger.info(f"[{trader.name}] 🔄 正在同步现有持仓...")
            account = await trader.client.get_account_info()
            positions = account.get('assetPositions', [])
            
            synced_count = 0
            for pos in positions:
                try:
                    if 'position' not in pos:
                        continue
                    
                    coin = pos['position']['coin']
                    size = float(pos['position']['szi'])
                    
                    if size == 0:
                        continue
                    
                    entry_px = float(pos['position']['entryPx'])
                    is_long = size > 0
                    abs_size = abs(size)
                    
                    trader.auto_trader.positions[coin] = {
                        'side': 'long' if is_long else 'short',
                        'entry_price': entry_px,
                        'size': abs_size,
                        'entry_time': datetime.now(),
                        'confidence': 0,
                        'reasoning': '系统启动时同步的历史持仓',
                        'order_id': 'synced'
                    }
                    
                    synced_count += 1
                    logger.info(f"[{trader.name}]    ✅ {coin} {'LONG' if is_long else 'SHORT'} {abs_size:.5f} @ ${entry_px:,.2f}")
                
                except Exception as e:
                    logger.warning(f"[{trader.name}] 解析持仓失败: {e}")
                    continue
            
            if synced_count > 0:
                logger.info(f"[{trader.name}] ✅ 已同步 {synced_count} 个现有持仓")
            else:
                logger.info(f"[{trader.name}] 📭 没有现有持仓")
        
        except Exception as e:
            logger.error(f"[{trader.name}] ❌ 同步持仓失败: {e}")
    
    async def get_consensus_decision(
        self, 
        coin: str, 
        market_data: Dict, 
        orderbook: Dict, 
        recent_trades: List,
        position_info: Optional[Dict] = None
    ) -> Tuple[Optional[TradingDecision], float, str, List[Dict]]:
        """获取组内共识决策"""
        kline_history_data = self.kline_manager.format_for_prompt(max_rows=16)
        
        async def get_ai_decision(ai_trader):
            try:
                ai_name = ai_trader.__class__.__name__.replace('Trader', '')
                logger.info(f"[{self.name}] 🤖 正在获取 {ai_name} 的决策...")
                
                original_create_prompt = ai_trader.create_market_prompt
                def wrapped_prompt(c, m, o, p=None, kline_history=None):
                    return original_create_prompt(c, m, o, p, kline_history=kline_history_data)
                ai_trader.create_market_prompt = wrapped_prompt
                
                decision, confidence, reasoning = await ai_trader.analyze_market(
                    coin, market_data, orderbook, recent_trades, position_info
                )
                
                ai_trader.create_market_prompt = original_create_prompt
                
                logger.info(f"[{self.name}]    {ai_name}: {decision} (信心: {confidence:.1f}%)")
                
                return {
                    'ai_name': ai_name,
                    'decision': decision,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
            
            except Exception as e:
                logger.error(f"[{self.name}] ❌ {ai_trader.__class__.__name__} 决策失败: {e}")
                return None
        
        logger.info(f"[{self.name}] 🚀 开始并行调用 {len(self.ai_traders)} 个AI模型...")
        results = await asyncio.gather(*[get_ai_decision(ai) for ai in self.ai_traders])
        
        ai_decisions = [r for r in results if r is not None]
        
        if not ai_decisions:
            return None, 0, "所有AI决策失败", []
        
        # 统计投票
        buy_votes = []
        sell_votes = []
        hold_votes = []
        
        for d in ai_decisions:
            if d['decision'] in [TradingDecision.BUY, TradingDecision.STRONG_BUY]:
                buy_votes.append(d)
            elif d['decision'] in [TradingDecision.SELL, TradingDecision.STRONG_SELL]:
                sell_votes.append(d)
            else:
                hold_votes.append(d)
        
        buy_count = len(buy_votes)
        sell_count = len(sell_votes)
        hold_count = len(hold_votes)
        
        vote_counts = [
            (buy_count, TradingDecision.BUY, buy_votes, "Buy"),
            (sell_count, TradingDecision.SELL, sell_votes, "Sell"),
            (hold_count, TradingDecision.HOLD, hold_votes, "Hold")
        ]
        vote_counts.sort(key=lambda x: x[0], reverse=True)
        
        vote_count, consensus_decision, supporting_ais, direction_name = vote_counts[0]
        
        if supporting_ais:
            avg_confidence = sum(d['confidence'] for d in supporting_ais) / len(supporting_ais)
        else:
            avg_confidence = 0
        
        vote_summary = f"Buy: {buy_count}, Sell: {sell_count}, Hold: {hold_count}"
        consensus_summary = f"Consensus: {direction_name} ({vote_count}/{len(ai_decisions)} votes, Avg Confidence {avg_confidence:.1f}%)\nVoting Details: {vote_summary}"
        
        logger.info(f"[{self.name}] 📊 {consensus_summary}")
        
        min_votes = settings.consensus_min_votes
        if vote_count >= min_votes:
            logger.info(f"[{self.name}] ✅ Consensus reached! Executing: {direction_name} ({consensus_decision})")
            return consensus_decision, avg_confidence, consensus_summary, ai_decisions
        else:
            logger.info(f"[{self.name}] ⚠️  No consensus reached (need at least {min_votes} votes), holding position")
            return TradingDecision.HOLD, avg_confidence, f"No consensus reached (need {min_votes} votes, got {vote_count} votes max), holding\n{vote_summary}", ai_decisions
    
    async def execute_decision_on_all_platforms(
        self, 
        coin: str, 
        decision: TradingDecision, 
        confidence: float, 
        reasoning: str, 
        current_price: float
    ):
        """在所有平台上执行决策"""
        if decision == TradingDecision.HOLD:
            logger.debug(f"[{self.name}] 💤 AI 建议观望，不执行交易")
            return
        
        logger.info(f"[{self.name}] 🚀 在所有平台上执行决策: {decision}")
        results = await self.multi_trader.execute_decision_all(
            coin, decision, confidence, reasoning, current_price, self.name
        )
        
        for platform_name, result in results.items():
            if result:
                logger.info(f"[{platform_name}] ✅ 交易已执行")
            else:
                logger.info(f"[{platform_name}] ⚠️  交易未执行")
    
    async def update_stats(self):
        """更新统计数据"""
        await self.multi_trader.update_all_stats()
        
        # 更新组统计
        comparison = self.multi_trader.get_comparison_stats()
        self.stats["platform_comparison"] = comparison
        
        # 为每个平台更新统计
        for platform_name, trader in self.multi_trader.platform_traders.items():
            self.stats["platforms"][platform_name] = trader.stats


class ConsensusArena:
    """共识竞技场 - 多平台版本（支持组共识 + 独立AI交易者）"""
    
    def __init__(self):
        self.groups: List[AIGroup] = []
        self.individual_traders: List[IndividualAITrader] = []
        self.running = False
        self.update_interval = settings.consensus_interval
        self.decision_history = []  # 决策历史记录（全局）
        self.balance_history = []   # 余额历史记录（全局）
    
    async def initialize(self):
        """初始化系统"""
        logger.info("=" * 80)
        logger.info("🤖 AI共识交易系统 - 多平台对比版")
        logger.info("=" * 80)
        
        enabled_platforms = get_enabled_platforms()
        logger.info(f"启用的交易平台: {', '.join(enabled_platforms)}")
        
        # 根据启用的交易模式显示不同的币种信息
        if not settings.enable_consensus_trading and not settings.enable_individual_trading:
            # 纯新闻驱动模式：显示新闻监控的币种
            try:
                from news_trading.config import SUPPORTED_COINS
                logger.info(f"📡 新闻监控币种: {', '.join(sorted(SUPPORTED_COINS))}")
            except ImportError:
                logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        else:
            # 常规交易模式：显示常规交易币种
            logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        
        logger.info(f"⏱️  决策周期: {self.update_interval//60}分钟")
        logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意才执行")
        logger.info(f"每组初始资金: ${settings.ai_initial_balance}")
        logger.info("=" * 80)
        
        # 检查是否启用共识交易
        if not settings.enable_consensus_trading:
            logger.info("\n🚫 共识交易已禁用，跳过Alpha/Beta组初始化")
        else:
            # 初始化 Alpha 组
            logger.info("\n📊 初始化 Alpha 组 (DeepSeek + Claude + Grok)...")
            alpha_ais = [
                DeepSeekTrader(api_key=settings.deepseek_api_key),
                ClaudeTrader(api_key=settings.claude_api_key),
                GrokTrader(api_key=settings.grok_api_key)
            ]
            alpha_group = AIGroup(
                settings.group_1_name,
                alpha_ais,
                settings.group_1_private_key
            )
            await alpha_group.initialize()
            await alpha_group.update_stats()  # 更新初始统计数据
            self.groups.append(alpha_group)
            logger.info(f"✅ Alpha组初始化完成")
            
            # 初始化 Beta 组
            logger.info("\n📊 初始化 Beta 组 (GPT-4 + Gemini + Qwen)...")
            beta_ais = [
                GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model),
                GeminiTrader(api_key=settings.gemini_api_key),
                QwenTrader(api_key=settings.qwen_api_key)
            ]
            beta_group = AIGroup(
                settings.group_2_name,
                beta_ais,
                settings.group_2_private_key
            )
            await beta_group.initialize()
            await beta_group.update_stats()  # 更新初始统计数据
            self.groups.append(beta_group)
            logger.info(f"✅ Beta组初始化完成")
        
        # 初始化独立AI交易者
        # 如果启用了独立交易或消息驱动交易，都需要初始化独立AI交易者
        # 通过检查是否配置了NEWS_TRADING_AIS来判断是否启用消息驱动交易
        news_trading_enabled = bool(get_news_trading_ais())
        need_individual_traders = settings.enable_individual_trading or news_trading_enabled
        
        if not need_individual_traders:
            logger.info("\n🚫 独立AI常规交易和消息驱动交易均已禁用，跳过独立AI交易者初始化")
        else:
            if not settings.enable_individual_trading and news_trading_enabled:
                logger.info("\n📢 为消息驱动交易初始化独立AI交易者...")
            
            try:
                individual_configs = get_individual_traders_config()
            except ValueError as e:
                logger.error(f"\n❌ 独立AI交易者配置错误:")
                logger.error(str(e))
                logger.error("\n请检查 .env 文件中的独立AI交易者私钥配置")
                return False
            
            # 如果仅消息驱动模式，只初始化NEWS_TRADING_AIS中配置的AI
            if not settings.enable_individual_trading and news_trading_enabled:
                news_trading_ais = get_news_trading_ais()
                individual_configs = [
                    config for config in individual_configs 
                    if config["ai_name"].lower() in news_trading_ais
                ]
                logger.info(f"🎯 仅初始化消息驱动交易所需的AI: {news_trading_ais}")
            
            if individual_configs:
                logger.info(f"\n🎯 初始化 {len(individual_configs)} 个独立AI交易者...")
                for config in individual_configs:
                    ai_name = config["ai_name"]
                    private_key = config["private_key"]
                    
                    logger.info(f"\n  初始化 {ai_name}-Solo...")
                    
                    # 创建AI实例
                    ai_instance = self._create_ai_instance(ai_name)
                    if not ai_instance:
                        error_msg = (
                            f"❌ 无法创建 {ai_name} AI实例\n"
                            f"   可能原因：\n"
                            f"   1. AI模型名称不支持\n"
                            f"   2. 对应的API密钥未配置或无效\n"
                            f"   请检查 .env 文件中的 {ai_name.upper()}_API_KEY 配置"
                        )
                        logger.error(error_msg)
                        return False
                    
                    # 创建独立交易者
                    try:
                        trader = IndividualAITrader(
                            name=f"{ai_name}-Solo",
                            ai_trader=ai_instance,
                            private_key=private_key
                        )
                        await trader.initialize()
                        await trader.update_stats()  # 更新初始统计数据
                        self.individual_traders.append(trader)
                        logger.info(f"  ✅ {ai_name}-Solo 初始化成功")
                    except Exception as e:
                        error_msg = (
                            f"❌ {ai_name}-Solo 初始化失败: {e}\n"
                            f"   可能原因：\n"
                            f"   1. 私钥格式错误\n"
                            f"   2. 账户余额不足\n"
                            f"   3. 网络连接问题\n"
                            f"   请检查私钥和账户状态"
                        )
                        logger.error(error_msg)
                        import traceback
                        logger.error(traceback.format_exc())
                        return False
        
        total_participants = len(self.groups) + len(self.individual_traders)
        logger.info(f"\n🚀 系统初始化完成！共 {len(self.groups)} 个组 + {len(self.individual_traders)} 个独立交易者 = {total_participants} 个参与者")
        return True
    
    def _create_ai_instance(self, ai_name: str):
        """根据AI名称创建AI实例"""
        ai_name_lower = ai_name.lower()
        
        if ai_name_lower == "deepseek":
            return DeepSeekTrader(api_key=settings.deepseek_api_key)
        elif ai_name_lower == "claude":
            return ClaudeTrader(api_key=settings.claude_api_key)
        elif ai_name_lower == "grok":
            return GrokTrader(api_key=settings.grok_api_key)
        elif ai_name_lower in ["gpt", "gpt4", "gpt-4"]:
            return GPTTrader(api_key=settings.openai_api_key, model=settings.gpt_model)
        elif ai_name_lower == "gemini":
            return GeminiTrader(api_key=settings.gemini_api_key)
        elif ai_name_lower == "qwen":
            return QwenTrader(api_key=settings.qwen_api_key)
        else:
            return None
    
    async def decision_loop(self):
        """共识决策循环"""
        loop_count = 0
        trading_symbol = symbol_filter.get_default_symbol()
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"🤖 共识决策循环 #{loop_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*80}")
                
                # 获取市场数据（使用第一个组的第一个平台客户端）
                try:
                    primary_client = self.groups[0].primary_client
                    if not primary_client:
                        logger.error("❌ 没有可用的交易客户端")
                        await asyncio.sleep(30)
                        continue
                    
                    market_data = await primary_client.get_market_data(trading_symbol)
                    current_price = market_data['price']
                    logger.info(f"💰 {trading_symbol} 价格: ${current_price:,.2f}")
                    logger.info(f"📈 24h涨跌: {market_data.get('change_24h', 0):+.2f}%")
                    
                    orderbook_data = await primary_client.get_orderbook(trading_symbol)
                    recent_trades = await primary_client.get_recent_trades(trading_symbol, limit=10)
                except Exception as e:
                    logger.error(f"❌ 获取市场数据失败: {e}")
                    await asyncio.sleep(30)
                    continue
                
                # 并行处理各组
                async def process_group(group):
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"📊 {group.name} 开始共识决策")
                        logger.info(f"{'─'*80}")
                        
                        # 更新K线
                        group.kline_manager.update_price(
                            price=current_price,
                            volume=market_data.get('volume', 0)
                        )
                        
                        # 获取共识决策（使用任意平台的持仓信息即可）
                        first_trader = list(group.multi_trader.platform_traders.values())[0]
                        position_info = first_trader.auto_trader.positions.get(trading_symbol)
                        
                        consensus_decision, confidence, summary, ai_votes = await group.get_consensus_decision(
                            trading_symbol, market_data, orderbook_data, recent_trades, position_info
                        )
                        
                        # 记录决策
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(consensus_decision),
                            "confidence": confidence,
                            "summary": summary,
                            "ai_votes": ai_votes,
                            "price": current_price
                        }
                        group.stats["consensus_decisions"].insert(0, decision_record)
                        group.stats["consensus_decisions"] = group.stats["consensus_decisions"][:100]
                        
                        # 记录到全局决策历史（用于前端展示）
                        # ai_votes 是一个列表，每个元素是 {'ai_name': xx, 'decision': xx, ...}
                        votes_count = sum(1 for vote in ai_votes if vote and vote.get('decision') == consensus_decision)
                        
                        # 格式化AI投票信息（用于前端展示）
                        formatted_ai_votes = []
                        for vote in ai_votes:
                            if vote:
                                formatted_ai_votes.append({
                                    "ai_name": vote.get('ai_name', 'Unknown'),
                                    "decision": str(vote.get('decision', '')),
                                    "confidence": round(vote.get('confidence', 0), 1),
                                    "reasoning": vote.get('reasoning', '')[:200]  # 限制长度
                                })
                        
                        global_decision = {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "group": group.name,
                            "direction": str(consensus_decision),
                            "confidence": round(confidence, 1),
                            "votes": votes_count,
                            "total_ais": len([v for v in ai_votes if v]),  # 过滤掉None
                            "price": current_price,
                            "platforms": [],
                            "ai_votes": formatted_ai_votes,
                            "summary": summary  # 添加共识总结
                        }
                        self.decision_history.insert(0, global_decision)
                        self.decision_history = self.decision_history[:100]  # 保留最近100条
                        
                        # 在所有平台上执行决策
                        await group.execute_decision_on_all_platforms(
                            trading_symbol,
                            consensus_decision,
                            confidence,
                            summary,
                            current_price
                        )
                        
                        # 更新统计
                        await group.update_stats()
                        
                        # 显示平台对比
                        if settings.platform_comparison_enabled:
                            logger.info(f"\n[{group.name}] 📊 平台收益对比:")
                            comparison = group.stats["platform_comparison"]
                            for platform_stats in comparison.get("platforms", []):
                                logger.info(f"  {platform_stats['name']}: "
                                          f"余额=${platform_stats['balance']:.2f}, "
                                          f"盈亏=${platform_stats['pnl']:+.2f}, "
                                          f"ROI={platform_stats['roi']:+.2f}%, "
                                          f"胜率={platform_stats['win_rate']:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"[{group.name}] ❌ 决策执行错误: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # 并行处理所有组（根据配置决定是否执行）
                if settings.enable_consensus_trading and self.groups:
                    await asyncio.gather(*[process_group(group) for group in self.groups])
                elif not settings.enable_consensus_trading:
                    logger.info("⏸️  共识交易已禁用，跳过Alpha/Beta组")
                
                # 并行处理所有独立AI交易者（根据配置决定是否执行）
                async def process_individual_trader(trader):
                    try:
                        logger.info(f"\n{'─'*80}")
                        logger.info(f"🎯 {trader.name} 开始独立决策")
                        logger.info(f"{'─'*80}")
                        
                        # 更新K线
                        trader.kline_manager.update_price(
                            price=current_price,
                            volume=market_data.get('volume', 0)
                        )
                        
                        # 获取持仓信息（使用任意平台的持仓信息即可）
                        first_trader = list(trader.multi_trader.platform_traders.values())[0]
                        position_info = first_trader.auto_trader.positions.get(trading_symbol)
                        
                        # 获取AI决策
                        decision, confidence, reasoning = await trader.get_decision(
                            trading_symbol, market_data, orderbook_data, recent_trades, position_info
                        )
                        
                        # 记录决策
                        decision_record = {
                            "time": datetime.now().isoformat(),
                            "decision": str(decision),
                            "confidence": confidence,
                            "reasoning": reasoning,
                            "price": current_price
                        }
                        trader.stats["decisions"].insert(0, decision_record)
                        trader.stats["decisions"] = trader.stats["decisions"][:100]
                        
                        # 记录到全局决策历史（用于前端展示）
                        global_decision = {
                            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "trader": trader.name,
                            "ai_name": trader.ai_name,
                            "type": "individual",
                            "direction": str(decision),
                            "confidence": round(confidence, 1),
                            "price": current_price,
                            "reasoning": reasoning[:200]  # 限制长度
                        }
                        self.decision_history.insert(0, global_decision)
                        self.decision_history = self.decision_history[:100]  # 保留最近100条
                        
                        # 在所有平台上执行决策
                        await trader.execute_decision_on_all_platforms(
                            trading_symbol,
                            decision,
                            confidence,
                            reasoning,
                            current_price
                        )
                        
                        # 更新统计
                        await trader.update_stats()
                        
                        # 显示平台对比
                        if settings.platform_comparison_enabled:
                            logger.info(f"\n[{trader.name}] 📊 平台收益对比:")
                            comparison = trader.stats["platform_comparison"]
                            for platform_stats in comparison.get("platforms", []):
                                logger.info(f"  {platform_stats['name']}: "
                                          f"余额=${platform_stats['balance']:.2f}, "
                                          f"盈亏=${platform_stats['pnl']:+.2f}, "
                                          f"ROI={platform_stats['roi']:+.2f}%, "
                                          f"胜率={platform_stats['win_rate']:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"[{trader.name}] ❌ 决策执行错误: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                if settings.enable_individual_trading and self.individual_traders:
                    await asyncio.gather(*[process_individual_trader(trader) for trader in self.individual_traders])
                elif not settings.enable_individual_trading:
                    logger.info("⏸️  独立AI交易已禁用，跳过独立AI")
                
                # 保存余额快照到 Redis
                try:
                    accounts = []
                    # 添加组账户
                    for group in self.groups:
                        for platform_name, trader in group.multi_trader.platform_traders.items():
                            accounts.append({
                                "group": group.name,
                                "platform": platform_name,
                                "type": "group",
                                "balance": trader.stats.get("balance", 0),
                                "pnl": trader.stats.get("pnl", 0),
                                "roi": trader.stats.get("roi", 0),
                                "total_trades": trader.stats.get("total_trades", 0)
                            })
                    
                    # 添加独立交易者账户
                    for individual_trader in self.individual_traders:
                        for platform_name, trader in individual_trader.multi_trader.platform_traders.items():
                            accounts.append({
                                "trader": individual_trader.name,
                                "ai_name": individual_trader.ai_name,
                                "platform": platform_name,
                                "type": "individual",
                                "balance": trader.stats.get("balance", 0),
                                "pnl": trader.stats.get("pnl", 0),
                                "roi": trader.stats.get("roi", 0),
                                "total_trades": trader.stats.get("total_trades", 0)
                            })
                    
                    if accounts:
                        redis_manager.save_balance_snapshot(accounts)
                except Exception as e:
                    logger.error(f"保存余额快照失败: {e}")
                
                logger.info(f"\n⏰ 等待 {self.update_interval} 秒后进行下一轮决策...")
                await asyncio.sleep(self.update_interval)
            
            except asyncio.CancelledError:
                logger.info("⏹️  决策循环被取消")
                break
            except Exception as e:
                logger.error(f"❌ 决策循环错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(30)
    
    async def start(self):
        """启动系统"""
        if await self.initialize():
            self.running = True
            
            # 检查是否启用常规交易
            if not settings.enable_consensus_trading and not settings.enable_individual_trading:
                logger.info("🚫 常规交易已禁用（仅消息驱动模式）")
                logger.info("📢 系统已初始化，等待消息触发...")
                # 不运行decision_loop，保持系统存活但不交易
                while self.running:
                    await asyncio.sleep(60)  # 保持存活
            else:
                logger.info("🚀 共识交易系统已启动")
                await self.decision_loop()
    
    async def stop(self):
        """停止系统"""
        self.running = False
        logger.info("🛑 共识交易系统正在停止...")
        
        # 关闭组的客户端
        for group in self.groups:
            # 关闭交易平台客户端
            for trader in group.multi_trader.platform_traders.values():
                await trader.client.close_session()
            # 关闭数据源客户端（如果存在）
            if hasattr(group, 'data_source_client') and group.data_source_client:
                await group.data_source_client.close_session()
        
        # 关闭独立AI交易者的客户端
        for individual_trader in self.individual_traders:
            # 关闭交易平台客户端
            for trader in individual_trader.multi_trader.platform_traders.values():
                await trader.client.close_session()
            # 关闭数据源客户端（如果存在）
            if hasattr(individual_trader, 'data_source_client') and individual_trader.data_source_client:
                await individual_trader.data_source_client.close_session()
        
        logger.info("✅ 共识交易系统已停止")


arena: Optional[ConsensusArena] = None


@app.on_event("startup")
async def startup_event():
    global arena
    arena = ConsensusArena()
    asyncio.create_task(arena.start())


@app.on_event("shutdown")
async def shutdown_event():
    if arena:
        await arena.stop()


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    if not arena:
        return {"status": "not_started"}
    
    # 更新所有组和交易者的统计数据（确保返回最新数据）
    for group in arena.groups:
        await group.update_stats()
    for trader in arena.individual_traders:
        await trader.update_stats()
    
    groups_data = []
    for group in arena.groups:
        group_info = {
            "type": "group",
            "group_name": group.stats["group_name"],
            "platforms": group.stats.get("platforms", {}),
            "platform_comparison": group.stats.get("platform_comparison", {}),
            "consensus_decisions": group.stats.get("consensus_decisions", [])
        }
        groups_data.append(group_info)
    
    individual_traders_data = []
    for trader in arena.individual_traders:
        # 获取平台地址信息
        platform_addresses = {}
        for platform_name, platform_trader in trader.multi_trader.platform_traders.items():
            if hasattr(platform_trader.client, 'address'):
                platform_addresses[platform_name] = platform_trader.client.address
        
        trader_info = {
            "type": "individual",
            "trader_name": trader.stats["trader_name"],
            "ai_name": trader.stats["ai_name"],
            "platforms": trader.stats.get("platforms", {}),
            "platform_comparison": trader.stats.get("platform_comparison", {}),
            "decisions": trader.stats.get("decisions", []),
            "addresses": platform_addresses  # 添加地址信息
        }
        individual_traders_data.append(trader_info)
    
    return {
        "status": "running" if arena.running else "stopped",
        "groups": groups_data,
        "individual_traders": individual_traders_data,
        "update_interval": f"{arena.update_interval//60}分钟",
        "consensus_rule": f"至少{settings.consensus_min_votes}个AI同意",
        "enabled_platforms": get_enabled_platforms(),
        "total_participants": len(arena.groups) + len(arena.individual_traders)
    }


@app.get("/api/platform_comparison")
async def get_platform_comparison():
    """获取平台对比数据"""
    if not arena:
        return {"platforms": []}
    
    # 汇总所有组的多平台数据
    platform_summary = {}
    
    for group in arena.groups:
        platforms = group.stats.get("platforms", {})
        for platform_name, platform_stats in platforms.items():
            # 提取平台简称（如 Hyperliquid 或 Aster）
            platform_key = "Hyperliquid" if "Hyperliquid" in platform_name else "Aster"
            
            if platform_key not in platform_summary:
                platform_summary[platform_key] = {
                    "platform": platform_key,
                    "total_pnl": 0,
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "initial_balance": 0,
                    "current_balance": 0
                }
            
            summary = platform_summary[platform_key]
            summary["total_pnl"] += platform_stats.get("total_pnl", 0)
            summary["total_trades"] += platform_stats.get("total_trades", 0)
            summary["wins"] += platform_stats.get("total_wins", 0)
            summary["losses"] += platform_stats.get("total_losses", 0)
            summary["initial_balance"] += platform_stats.get("initial_balance", 0)
            summary["current_balance"] += platform_stats.get("current_balance", 0)
    
    # 计算衍生指标
    platforms_list = []
    for platform_data in platform_summary.values():
        total_trades = platform_data["total_trades"]
        win_rate = (platform_data["wins"] / total_trades * 100) if total_trades > 0 else 0
        roi = (platform_data["total_pnl"] / platform_data["initial_balance"] * 100) if platform_data["initial_balance"] > 0 else 0
        
        platforms_list.append({
            "platform": platform_data["platform"],
            "total_pnl": platform_data["total_pnl"],
            "current_balance": platform_data["current_balance"],
            "initial_balance": platform_data["initial_balance"],
            "roi_percentage": roi,
            "win_rate": win_rate,
            "total_trades": total_trades
        })
    
    return {"platforms": platforms_list}


@app.get("/api/chart")
async def get_chart_data(
    symbol: str = settings.allowed_trading_symbols,
    interval: str = "15m",
    lookback: int = 100
):
    """获取K线图数据（包含多平台交易标记）"""
    try:
        if not arena or len(arena.groups) == 0:
            return {"error": "系统未启动"}
        
        # 从第一个组的第一个平台获取K线数据
        first_group = arena.groups[0]
        candles = []
        
        if first_group.primary_client:
            candles = await first_group.primary_client.get_candles(
                symbol,
                interval=interval,
                lookback=lookback
            )
        
        # 收集所有组的所有平台的交易标记
        trade_markers = []
        from datetime import datetime
        
        # 1. 收集组交易（Alpha组、Beta组）
        for group in arena.groups:
            group_start_time = group.start_time
            
            # 遍历该组的所有平台
            for platform_name, platform_stats in group.stats.get("platforms", {}).items():
                for trade in platform_stats.get("trades", []):
                    try:
                        trade_time = datetime.fromisoformat(trade.get("time", ""))
                        
                        # 只显示系统启动后的交易
                        if trade_time < group_start_time:
                            continue
                        
                        timestamp_ms = int(trade_time.timestamp() * 1000)
                        
                        # 对于开仓用price，对于平仓用exit_price
                        price = trade.get("price", 0) if trade.get("action") == "open" else trade.get("exit_price", 0)
                        
                        trade_markers.append({
                            "time": timestamp_ms,
                            "price": price,
                            "group": group.stats["group_name"],
                            "platform": platform_name,  # 添加平台信息
                            "action": trade.get("action", ""),
                            "side": trade.get("side", ""),
                            "size": trade.get("size", 0),
                            "pnl": trade.get("pnl", 0)  # 平仓交易才有pnl
                        })
                    except:
                        continue
        
        # 2. 收集独立交易者的交易（DeepSeek-Solo, Claude-Solo等）
        for trader in arena.individual_traders:
            trader_start_time = trader.start_time
            
            # 遍历该交易者的所有平台
            for platform_name, platform_stats in trader.stats.get("platforms", {}).items():
                for trade in platform_stats.get("trades", []):
                    try:
                        trade_time = datetime.fromisoformat(trade.get("time", ""))
                        
                        # 只显示系统启动后的交易
                        if trade_time < trader_start_time:
                            continue
                        
                        timestamp_ms = int(trade_time.timestamp() * 1000)
                        
                        # 对于开仓用price，对于平仓用exit_price
                        price = trade.get("price", 0) if trade.get("action") == "open" else trade.get("exit_price", 0)
                        
                        trade_markers.append({
                            "time": timestamp_ms,
                            "price": price,
                            "group": trader.stats["trader_name"],  # 使用交易者名称（如"Grok-Solo"）
                            "platform": platform_name,
                            "action": trade.get("action", ""),
                            "side": trade.get("side", ""),
                            "size": trade.get("size", 0),
                            "pnl": trade.get("pnl", 0)  # 平仓交易才有pnl
                        })
                    except:
                        continue
        
        # 🔍 统计各平台交易数量
        hl_count = sum(1 for m in trade_markers if 'Hyperliquid' in m.get('platform', ''))
        aster_count = sum(1 for m in trade_markers if 'Aster' in m.get('platform', ''))
        logger.info(f"📊 [K-line Markers] Total: {len(trade_markers)}, Hyperliquid: {hl_count}, Aster: {aster_count}")
        
        return {
            "candles": candles,
            "trade_markers": trade_markers,
            "symbol": symbol,
            "interval": interval
        }
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}


@app.get("/leaderboard")
async def get_leaderboard(metric: str = "total_pnl", limit: int = 10):
    """获取AI排行榜"""
    if not arena:
        return {"rankings": []}
    
    # 收集所有AI的统计数据
    ai_stats = []
    
    # 添加组内AI（注意：组内AI是共识决策，不单独统计PnL）
    for group in arena.groups:
        for ai_trader in group.ai_traders:
            ai_name = ai_trader.__class__.__name__.replace('Trader', '')
            stats = {
                "ai_name": ai_name,
                "type": "group_member",
                "group": group.stats["group_name"],
                "total_pnl": 0,
                "roi_percentage": 0,
                "win_rate": 0,
                "total_trades": 0
            }
            ai_stats.append(stats)
    
    # 添加独立AI交易者（有实际的交易统计）
    for trader in arena.individual_traders:
        # 汇总该交易者所有平台的统计
        total_pnl = 0
        total_trades = 0
        total_wins = 0
        total_initial = 0
        
        for platform_stats in trader.stats.get("platforms", {}).values():
            total_pnl += platform_stats.get("total_pnl", 0)
            total_trades += platform_stats.get("total_trades", 0)
            total_wins += platform_stats.get("total_wins", 0)
            total_initial += platform_stats.get("initial_balance", 0)
        
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        roi = (total_pnl / total_initial * 100) if total_initial > 0 else 0
        
        stats = {
            "ai_name": trader.ai_name,
            "type": "individual",
            "trader": trader.name,
            "total_pnl": total_pnl,
            "roi_percentage": roi,
            "win_rate": win_rate,
            "total_trades": total_trades
        }
        ai_stats.append(stats)
    
    # 按指标排序
    ai_stats.sort(key=lambda x: x.get(metric, 0), reverse=True)
    
    # 添加排名
    for i, stats in enumerate(ai_stats[:limit]):
        stats["rank"] = i + 1
    
    return {"rankings": ai_stats[:limit]}


@app.get("/leaderboard/summary")
async def get_leaderboard_summary():
    """获取排行榜摘要"""
    if not arena:
        return {}
    
    total_trades = 0
    total_pnl = 0
    
    # 统计组的数据
    for group in arena.groups:
        for platform_stats in group.stats.get("platforms", {}).values():
            total_trades += platform_stats.get("total_trades", 0)
            total_pnl += platform_stats.get("total_pnl", 0)
    
    # 统计独立AI交易者的数据
    for trader in arena.individual_traders:
        for platform_stats in trader.stats.get("platforms", {}).values():
            total_trades += platform_stats.get("total_trades", 0)
            total_pnl += platform_stats.get("total_pnl", 0)
    
    # 计算总AI数（组内AI + 独立AI）
    group_ais = len(arena.groups[0].ai_traders) * len(arena.groups) if arena.groups else 0
    individual_ais = len(arena.individual_traders)
    
    return {
        "total_ais": group_ais + individual_ais,
        "group_ais": group_ais,
        "individual_ais": individual_ais,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "active_groups": len(arena.groups),
        "active_individual_traders": len(arena.individual_traders)
    }


@app.get("/strategies")
async def get_strategies():
    """获取策略详情"""
    if not arena:
        return {"strategies": []}
    
    strategies = []
    
    # 添加组内AI策略
    for group in arena.groups:
        for ai_trader in group.ai_traders:
            ai_name = ai_trader.__class__.__name__.replace('Trader', '')
            strategy = {
                "name": ai_name,
                "type": "group_member",
                "group": group.stats["group_name"],
                "status": "active",
                "description": f"{ai_name} AI 交易策略 (组内共识)"
            }
            strategies.append(strategy)
    
    # 添加独立AI交易者策略
    for trader in arena.individual_traders:
        strategy = {
            "name": trader.ai_name,
            "type": "individual",
            "trader": trader.name,
            "status": "active",
            "description": f"{trader.ai_name} AI 交易策略 (独立决策)"
        }
        strategies.append(strategy)
    
    return {"strategies": strategies}


@app.get("/api/realtime_balance")
async def get_realtime_balance():
    """获取所有账户的实时余额"""
    if not arena:
        return {"accounts": []}
    
    accounts = []
    
    # 添加组账户
    for group in arena.groups:
        group_name = group.stats["group_name"]
        
        # 获取该组所有平台的余额
        for platform_name, platform_stats in group.stats.get("platforms", {}).items():
            # 提取平台简称（去掉组名前缀）
            platform_display = platform_name.replace(f"{group_name}-", "")
            
            account = {
                "type": "group",
                "group": group_name,
                "platform": platform_display,
                "balance": platform_stats.get("balance", 0),
                "initial_balance": platform_stats.get("initial_balance", 0),
                "pnl": platform_stats.get("pnl", 0),
                "roi": platform_stats.get("roi", 0),
                "trades": platform_stats.get("total_trades", 0)
            }
            accounts.append(account)
    
    # 添加独立AI交易者账户
    for trader in arena.individual_traders:
        trader_name = trader.stats["trader_name"]
        ai_name = trader.stats["ai_name"]
        
        # 获取该交易者所有平台的余额
        for platform_name, platform_stats in trader.stats.get("platforms", {}).items():
            # 提取平台简称（去掉交易者名前缀）
            platform_display = platform_name.replace(f"{trader_name}-", "")
            
            account = {
                "type": "individual",
                "trader": trader_name,
                "ai_name": ai_name,
                "platform": platform_display,
                "balance": platform_stats.get("balance", 0),
                "initial_balance": platform_stats.get("initial_balance", 0),
                "pnl": platform_stats.get("pnl", 0),
                "roi": platform_stats.get("roi", 0),
                "trades": platform_stats.get("total_trades", 0)
            }
            accounts.append(account)
    
    return {"accounts": accounts}


@app.get("/api/balance_history")
async def get_balance_history(limit: int = -1):
    """获取余额历史数据（从Redis）- 默认返回所有历史数据"""
    try:
        history = redis_manager.get_balance_history(limit=limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"获取余额历史失败: {e}")
        return {"history": [], "count": 0, "error": str(e)}


@app.get("/api/decisions")
async def get_decisions():
    """获取决策历史"""
    if not arena:
        return {"decisions": []}
    
    return {"decisions": arena.decision_history}


@app.get("/")
async def root():
    """根路径 - 根据配置显示不同页面"""
    from fastapi.responses import FileResponse
    
    # 如果只启用消息交易，显示新版新闻交易页面
    if settings.news_trading_enabled and not settings.enable_consensus_trading and not settings.enable_individual_trading:
        response = FileResponse("web/news_trading_v2.html")
    else:
        # 否则显示常规交易页面
        response = FileResponse("web/consensus_arena.html")
    
    # 禁用缓存，确保每次都加载最新版本
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.mount("/web", StaticFiles(directory="web"), name="web")


# ================== 消息驱动交易API ==================

@app.post("/api/news_trading/start")
async def start_news_trading(request: dict = None):
    """启动消息驱动交易系统（支持动态更新监控币种列表）"""
    global news_listeners, news_listener_tasks
    
    # 检查arena是否已初始化
    if not arena or not arena.individual_traders:
        return {"error": "Arena未启动或没有独立AI交易者"}
    
    try:
        # 获取前端传递的激活币种列表
        monitored_coins = []
        if request and 'coins' in request:
            monitored_coins = [coin.upper() for coin in request['coins']]
            logger.info(f"📡 前端激活的监控币种: {monitored_coins}")
        else:
            # 如果前端未传递，使用所有配置的币种
            from news_trading.config import SUPPORTED_COINS
            monitored_coins = [coin.upper() for coin in SUPPORTED_COINS]
            logger.info(f"📡 使用所有配置的监控币种: {monitored_coins}")
        
        # 获取配置的AI列表
        configured_ais = get_news_trading_ais()
        if not configured_ais:
            return {"error": "请在.env中配置NEWS_TRADING_AIS（如: claude,gpt,deepseek）"}
        
        # 准备API密钥字典
        ai_api_keys = {
            "claude": settings.claude_api_key,
            "gpt": settings.openai_api_key,
            "gpt4": settings.openai_api_key,
            "deepseek": settings.deepseek_api_key,
            "gemini": settings.gemini_api_key,
            "grok": settings.grok_api_key,
            "qwen": settings.qwen_api_key
        }
        
        # 🔧 如果系统已在运行，只更新监控币种列表
        if news_listeners:
            news_handler.setup(
                individual_traders=arena.individual_traders,
                configured_ais=configured_ais,
                ai_api_keys=ai_api_keys,
                monitored_coins=monitored_coins  # 更新监控币种列表
            )
            logger.info(f"✅ 已更新监控币种列表: {monitored_coins}")
            return {
                "message": "监控币种列表已更新",
                "monitored_coins": monitored_coins,
                "active_ais": list(news_handler.analyzers.keys())
            }
        
        # 首次启动：配置处理器
        news_handler.setup(
            individual_traders=arena.individual_traders,
            configured_ais=configured_ais,
            ai_api_keys=ai_api_keys,
            monitored_coins=monitored_coins  # 传递监控币种列表
        )
        
        # 创建消息监听器
        news_listeners = [
            create_binance_spot_listener(news_handler.handle_message),
            create_binance_futures_listener(news_handler.handle_message),
            create_binance_alpha_listener(news_handler.handle_message),
            create_upbit_listener(news_handler.handle_message),
            create_coinbase_listener(news_handler.handle_message)
        ]
        
        # 启动所有监听器
        for listener in news_listeners:
            task = asyncio.create_task(listener.start())
            news_listener_tasks.append(task)
            logger.info(f"✅ 启动监听器: {listener.__class__.__name__}")
        
        logger.info(f"🚀 消息交易系统已启动，激活的AI: {list(news_handler.analyzers.keys())}")
        
        return {
            "message": "消息交易系统已启动",
            "active_ais": list(news_handler.analyzers.keys()),
            "listeners": len(news_listeners)
        }
    
    except Exception as e:
        logger.error(f"❌ 启动消息交易系统失败: {e}", exc_info=True)
        return {"error": str(e)}


@app.get("/api/news_trading/ai_models")
async def get_ai_models():
    """获取AI模型列表及激活状态"""
    try:
        from news_trading.logo_config import get_ai_model_logo
        from config.settings import get_news_trading_ais
        
        active_ais = get_news_trading_ais()
        
        ai_models = [
            {
                "name": "GPT-4o",
                "provider": "OpenAI",
                "logo": get_ai_model_logo("GPT-4o"),
                "active": "gpt" in active_ais,
                "key": "gpt"
            },
            {
                "name": "Gemini 2.0",
                "provider": "Google",
                "logo": get_ai_model_logo("Gemini-2.0-Flash"),
                "active": "gemini" in active_ais,
                "key": "gemini"
            },
            {
                "name": "Grok-4",
                "provider": "xAI",
                "logo": get_ai_model_logo("Grok-4-Fast"),
                "active": "grok" in active_ais,
                "key": "grok"
            },
            {
                "name": "DeepSeek",
                "provider": "DeepSeek AI",
                "logo": get_ai_model_logo("DeepSeek"),
                "active": "deepseek" in active_ais,
                "key": "deepseek"
            },
            {
                "name": "Claude 3.5",
                "provider": "Anthropic",
                "logo": get_ai_model_logo("Claude-3.5"),
                "active": "claude" in active_ais,
                "key": "claude"
            },
            {
                "name": "Qwen Max",
                "provider": "Alibaba",
                "logo": get_ai_model_logo("Qwen-Max"),
                "active": "qwen" in active_ais,
                "key": "qwen"
            }
        ]
        
        return {"ai_models": ai_models}
    
    except Exception as e:
        logger.error(f"❌ 获取AI模型失败: {e}", exc_info=True)
        return {"error": str(e), "ai_models": []}


@app.get("/api/news_trading/coins")
async def get_monitored_coins():
    """获取所有监控的币种及其档案"""
    try:
        from news_trading.coin_profiles import COIN_PROFILES, get_coin_profile
        from news_trading.logo_config import get_coin_logo, get_platform_logo, get_news_source_logo
        
        # 直接从COIN_PROFILES获取所有币种（包含动态添加的）
        coins = list(COIN_PROFILES.keys())
        profiles = []
        
        for coin in coins:
            profile = get_coin_profile(coin)
            # 转换枚举为字符串，并添加Logo
            profile_data = {
                "symbol": coin,
                "name": profile["name"],
                "full_name": profile["full_name"],
                "description": profile["description"],
                "logo": get_coin_logo(coin),
                "background": profile["background"],
                "upside_potential": profile["upside_potential"],
                "trading_platforms": [
                    {"name": p.value, "logo": get_platform_logo(p.value)} 
                    for p in profile["trading_platforms"]
                ],
                "news_sources": [
                    {"name": s.value, "logo": get_news_source_logo(s.value)} 
                    for s in profile["news_sources"]
                ],
                "why_monitor": profile["why_monitor"]
            }
            profiles.append(profile_data)
        
        return {"coins": profiles}
    
    except Exception as e:
        logger.error(f"❌ 获取币种档案失败: {e}", exc_info=True)
        return {"error": str(e), "coins": []}


@app.get("/api/news_trading/coins/{coin_symbol}")
async def get_coin_profile_api(coin_symbol: str):
    """获取指定币种的详细档案"""
    try:
        from news_trading.coin_profiles import get_coin_profile
        from news_trading.logo_config import get_coin_logo, get_platform_logo, get_news_source_logo, get_ai_model_logo
        
        profile = get_coin_profile(coin_symbol)
        
        # 模拟预测数据（后续可从数据库读取）
        import random
        has_prediction = random.choice([True, False])  # 50%概率有预测
        prediction_count = random.randint(5, 50) if has_prediction else 0
        prediction_bullish = random.randint(40, 80) if has_prediction else 0
        prediction_bearish = 100 - prediction_bullish if has_prediction else 0
        
        # 转换枚举为字符串，并添加Logo
        return {
            "symbol": coin_symbol.upper(),
            "name": profile["name"],
            "full_name": profile["full_name"],
            "description": profile["description"],
            "logo": get_coin_logo(coin_symbol),
            "twitter": profile.get("twitter", ""),
            "background": profile["background"],
            "project_type": profile["project_type"].value if hasattr(profile["project_type"], "value") else profile["project_type"],
            "current_stage": profile["current_stage"].value if hasattr(profile["current_stage"], "value") else profile["current_stage"],
            "next_stage": profile["next_stage"].value if hasattr(profile["next_stage"], "value") else profile["next_stage"],
            "stage_progress": profile["stage_progress"],
            "stage_links": profile.get("stage_links", {}),
            "upside_potential": profile["upside_potential"],
            # 预测相关数据
            "has_prediction": has_prediction,
            "prediction_count": prediction_count,
            "prediction_bullish": prediction_bullish,
            "prediction_bearish": prediction_bearish,
            "trading_platforms": [
                {"name": p.value, "logo": get_platform_logo(p.value)} 
                for p in profile["trading_platforms"]
            ],
            "news_sources": [
                {"name": s.value, "logo": get_news_source_logo(s.value)} 
                for s in profile["news_sources"]
            ],
            "ai_models": [
                {
                    "name": "GPT-4o", 
                    "logo": get_ai_model_logo("GPT-4o"),
                    "active": "gpt" in get_news_trading_ais()
                },
                {
                    "name": "Gemini-2.0-Flash", 
                    "logo": get_ai_model_logo("Gemini-2.0-Flash"),
                    "active": "gemini" in get_news_trading_ais()
                },
                {
                    "name": "Grok-4-Fast", 
                    "logo": get_ai_model_logo("Grok-4-Fast"),
                    "active": "grok" in get_news_trading_ais()
                },
                {
                    "name": "DeepSeek", 
                    "logo": get_ai_model_logo("DeepSeek"),
                    "active": "deepseek" in get_news_trading_ais()
                },
                {
                    "name": "Claude-3.5", 
                    "logo": get_ai_model_logo("Claude-3.5"),
                    "active": "claude" in get_news_trading_ais()
                },
                {
                    "name": "Qwen-Max", 
                    "logo": get_ai_model_logo("Qwen-Max"),
                    "active": "qwen" in get_news_trading_ais()
                },
            ],
            "why_monitor": profile["why_monitor"]
        }
    
    except Exception as e:
        logger.error(f"❌ 获取币种档案失败: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/news_trading/submit_coin_full")
async def submit_coin_full(request: dict):
    """接收用户提交的完整币种信息并动态创建币种配置"""
    try:
        import json
        from datetime import datetime
        from news_trading.coin_profiles import COIN_PROFILES, ProjectType, ProjectStage, TradingPlatform, NewsSource
        
        # 验证必填字段
        required_fields = ['symbol', 'name', 'project_type', 'twitter', 'trading_link']
        for field in required_fields:
            if not request.get(field):
                return {"error": f"Missing required field: {field}"}
        
        symbol = request['symbol'].upper()
        
        # 检查是否已存在
        if symbol in COIN_PROFILES:
            return {"error": f"Coin {symbol} already exists"}
        
        # 根据project_type确定项目类型和阶段
        project_type_map = {
            'mega': ProjectType.MEGA,
            'normal': ProjectType.NORMAL,
            'meme': ProjectType.MEME
        }
        project_type = project_type_map.get(request['project_type'], ProjectType.NORMAL)
        
        # 根据项目类型确定当前阶段
        if project_type == ProjectType.MEGA:
            current_stage = ProjectStage.PRE_MARKET
            next_stage = ProjectStage.CEX_SPOT
            stage_upcoming = "CEX Spot Listing (Community Submission)"
        else:
            current_stage = ProjectStage.ON_CHAIN
            next_stage = ProjectStage.CEX_ALPHA
            stage_upcoming = "CEX Alpha + Futures (Community Submission)"
        
        # 创建新的币种配置
        new_coin_profile = {
            "name": symbol,
            "full_name": request['name'],
            "description": f"Community submitted: {request['name']}",
            "twitter": request['twitter'],
            "background": {
                "total_funding": "Community Submission",
                "track": "Community Token",
                "lead_investors": "Community-driven"
            },
            "project_type": project_type,
            "current_stage": current_stage,
            "next_stage": next_stage,
            "stage_progress": {
                "completed": [],
                "current": current_stage.value,
                "upcoming": stage_upcoming
            },
            "stage_links": {},  # 将在下面根据trading_link填充
            "upside_potential": {
                "market_position": "Community submitted token",
                "narrative": "User-generated content",
                "catalysts": ["Community support", "Platform listings"],
                "risk_factors": ["Community submission - DYOR"],
                "target_multiplier": "TBD"
            },
            "trading_platforms": [TradingPlatform.HYPERLIQUID, TradingPlatform.ASTER],
            "news_sources": [
                NewsSource.BINANCE_SPOT,
                NewsSource.BINANCE_FUTURES,
                NewsSource.UPBIT,
                NewsSource.USER_SUBMIT
            ],
            "why_monitor": f"Community submitted token: {request['name']}. Trading link: {request['trading_link']}"
        }
        
        # 根据trading_link自动填充stage_links
        trading_link = request['trading_link']
        stage_name = current_stage.value  # 例如："On-chain Trading"
        
        # 检测交易平台并生成相应的链接
        platform_info = None
        if 'uniswap' in trading_link.lower():
            platform_info = {
                "platform": "Uniswap V4" if "v4" in trading_link.lower() else "Uniswap",
                "platform_short": "Uni",
                "url": trading_link,
                "logo": "/images/trade_platforms/uniswap.png"
            }
        elif 'pancakeswap' in trading_link.lower():
            platform_info = {
                "platform": "PancakeSwap",
                "platform_short": "Cake",
                "url": trading_link,
                "logo": "/images/trade_platforms/pancakeswap.png"
            }
        elif 'raydium' in trading_link.lower():
            platform_info = {
                "platform": "Raydium",
                "platform_short": "Ray",
                "url": trading_link,
                "logo": "/images/raydium.jpg"
            }
        elif 'hyperliquid' in trading_link.lower():
            platform_info = {
                "platform": "Hyperliquid",
                "platform_short": "HL",
                "url": trading_link,
                "logo": "/images/hyperliquid.png"
            }
        elif 'aster' in trading_link.lower():
            platform_info = {
                "platform": "Aster",
                "platform_short": "AS",
                "url": trading_link,
                "logo": "/images/aster.jpg"
            }
        else:
            # 通用链接
            platform_info = {
                "platform": "Trading Platform",
                "platform_short": "DEX",
                "url": trading_link,
                "logo": None
            }
        
        if platform_info:
            new_coin_profile["stage_links"][stage_name] = [platform_info]
        
        # 尝试获取Twitter头像作为Logo
        from news_trading.logo_fetcher import fetch_twitter_avatar, get_default_logo
        from news_trading.logo_config import COIN_LOGOS
        
        logo_path = None
        if request['twitter']:
            try:
                logo_path = await fetch_twitter_avatar(request['twitter'], symbol)
                if logo_path:
                    logger.info(f"✅ 成功获取 {symbol} 的Twitter头像: {logo_path}")
                    # 动态添加到COIN_LOGOS字典中
                    COIN_LOGOS[symbol] = logo_path
            except Exception as e:
                logger.warning(f"⚠️ 获取Twitter头像失败: {e}")
        
        # 如果没有获取到logo，会在前端使用默认SVG占位符
        
        # 动态添加到COIN_PROFILES
        COIN_PROFILES[symbol] = new_coin_profile
        
        # 同时添加到SUPPORTED_COINS
        from news_trading.config import SUPPORTED_COINS
        if symbol not in SUPPORTED_COINS:
            SUPPORTED_COINS.append(symbol)
        
        # 保存提交记录
        submission = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "name": request['name'],
            "project_type": request['project_type'],
            "twitter": request['twitter'],
            "trading_link": request['trading_link'],
            "status": "active"
        }
        
        submissions_file = "coin_submissions.json"
        try:
            with open(submissions_file, 'r') as f:
                submissions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            submissions = []
        
        submissions.append(submission)
        
        with open(submissions_file, 'w') as f:
            json.dump(submissions, f, indent=2)
        
        logger.info(f"✅ 新币种添加成功: {symbol} - {request['name']}")
        
        # 🚀 预加载精度配置和开仓参数（优化首次交易速度）
        preload_success = False
        preload_time = 0
        try:
            import time
            from trading.precision_config import PrecisionConfig
            
            logger.info(f"🔄 [{symbol}] 正在预加载精度配置和市场数据...")
            start_time = time.time()
            
            # 预加载 Hyperliquid 精度配置（会缓存起来）
            precision_config = PrecisionConfig.get_hyperliquid_precision(symbol)
            
            # 预加载市场数据（包括最大杠杆）
            if 'hyperliquid' in trading_link.lower() or 'aster' not in trading_link.lower():
                try:
                    from trading.hyperliquid.client import HyperliquidClient
                    from config.settings import settings
                    
                    hl_client = HyperliquidClient(settings.hyperliquid_private_key)
                    market_data = hl_client.get_market_data(symbol)
                    
                    preload_time = time.time() - start_time
                    logger.info(
                        f"✅ [{symbol}] 预加载完成 ({preload_time:.2f}s)\n"
                        f"   价格精度: {precision_config.get('price_precision')}位\n"
                        f"   数量精度: {precision_config.get('quantity_precision')}位\n"
                        f"   最大杠杆: {market_data.get('maxLeverage', 'N/A')}x\n"
                        f"   当前价格: ${market_data.get('mid_price', 'N/A')}"
                    )
                    preload_success = True
                except Exception as e:
                    logger.warning(f"⚠️ [{symbol}] 预加载市场数据失败: {e}")
                    # 精度配置已缓存，只是市场数据失败
                    preload_time = time.time() - start_time
                    preload_success = True  # 精度配置成功就算成功
            else:
                preload_time = time.time() - start_time
                logger.info(f"✅ [{symbol}] 精度配置已缓存 ({preload_time:.2f}s)")
                preload_success = True
                
        except Exception as e:
            preload_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.warning(f"⚠️ [{symbol}] 预加载失败: {e}，首次开仓可能较慢")
        
        return {
            "success": True,
            "message": "Coin added successfully and is now available for monitoring",
            "symbol": symbol,
            "coin": {
                "symbol": symbol,
                "name": request['name'],
                "project_type": request['project_type']
            },
            "preload": {
                "success": preload_success,
                "time": round(preload_time, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ 添加新币种失败: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/news_trading/submit_url")
async def submit_url(request: dict):
    """接收用户提交的URL（新闻链接或项目链接）"""
    try:
        from datetime import datetime
        
        url = request.get('url')
        if not url:
            return {"error": "Missing required field: url"}
        
        logger.info(f"📬 收到用户提交的URL: {url}")
        
        # 抓取URL内容
        content = await scrape_url_content(url)
        
        if not content:
            return {"error": "Failed to fetch content from URL"}
        
        # 创建用户提交消息
        from news_trading.message_listeners.base_listener import ListingMessage
        
        # 尝试从内容中提取币种符号
        from news_trading.config import SUPPORTED_COINS
        coin_symbols = []
        for coin in SUPPORTED_COINS:
            if coin.upper() in content.upper():
                coin_symbols.append(coin.upper())
        
        # 如果找到币种，创建消息并触发处理
        if coin_symbols and news_handler:
            for coin_symbol in coin_symbols[:1]:  # 只处理第一个匹配的币种
                message = ListingMessage(
                    source="user_submit",
                    coin_symbol=coin_symbol,
                    raw_message=f"User submitted: {content[:200]}...",
                    timestamp=datetime.now(),
                    url=url,
                    reliability_score=0.7  # 用户提交可靠性中等
                )
                
                # 触发处理
                await news_handler.handle_message(message)
                
                logger.info(f"✅ 用户提交已触发AI分析: {coin_symbol}")
                
                return {
                    "success": True,
                    "message": "URL submitted and AI analysis triggered",
                    "coin_symbol": coin_symbol,
                    "url": url
                }
        
        # 如果没有找到币种，仍然记录提交
        logger.warning(f"⚠️ 用户提交的URL未识别到支持的币种: {url}")
        
        return {
            "success": True,
            "message": "URL received but no supported coin detected",
            "url": url
        }
    
    except Exception as e:
        logger.error(f"❌ 处理URL提交失败: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/news_trading/stop")
async def stop_news_trading():
    """停止消息驱动交易系统"""
    global news_listeners, news_listener_tasks
    
    if not news_listeners:
        return {"message": "消息交易系统未运行"}
    
    try:
        # 停止所有监听器
        for listener in news_listeners:
            await listener.stop()
        
        # 取消所有任务
        for task in news_listener_tasks:
            task.cancel()
        
        await asyncio.gather(*news_listener_tasks, return_exceptions=True)
        
        news_listeners = []
        news_listener_tasks = []
        
        logger.info("✅ 消息交易系统已停止")
        return {"message": "消息交易系统已停止"}
    
    except Exception as e:
        logger.error(f"❌ 停止消息交易系统失败: {e}", exc_info=True)
        return {"error": str(e)}


@app.post("/api/news_trading/submit")
async def submit_user_news(url: str, coin: str):
    """
    用户提交消息
    
    Args:
        url: 消息URL
        coin: 币种符号
    """
    try:
        logger.info(f"📥 收到用户提交的消息: {coin} - {url}")
        
        # 验证币种
        if not is_supported_coin(coin.upper()):
            return {
                "success": False,
                "error": f"不支持的币种: {coin}。请在news_trading/config.py的COIN_MAPPING中添加"
            }
        
        # 爬取URL内容
        content = await scrape_url_content(url)
        
        if not content:
            return {
                "success": False,
                "error": "无法获取URL内容，请检查链接是否有效"
            }
        
        # 构造消息
        message = ListingMessage(
            source="user_submitted",
            coin_symbol=coin.upper(),
            raw_message=content[:500] + "..." if len(content) > 500 else content,  # 显示预览
            timestamp=datetime.now(),
            url=url,
            reliability_score=0.8  # 用户提交消息可靠性中等
        )
        
        # 处理消息
        await news_handler.handle_message(message)
        
        return {
            "success": True,
            "message": f"消息已提交，{len(news_handler.analyzers)}个AI正在分析",
            "coin": coin.upper(),
            "url": url,
            "content_preview": content[:200] + "..." if len(content) > 200 else content
        }
    
    except Exception as e:
        logger.error(f"❌ 处理用户提交消息失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/news_trading/events")
async def news_trading_events(request: Request):
    """
    SSE端点 - 推送新闻交易实时事件
    """
    from news_trading.event_manager import event_manager
    import json
    
    async def event_generator():
        # 创建订阅队列
        queue = asyncio.Queue()
        event_manager.add_subscriber(queue)
        
        try:
            # 首先发送历史事件
            history = event_manager.get_history()
            for event in history[-10:]:  # 只发送最近10条
                yield f"data: {json.dumps(event)}\n\n"
            
            # 持续推送新事件
            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break
                
                try:
                    # 等待新事件（带超时，用于定期检查连接）
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f": heartbeat\n\n"
                    
        except Exception as e:
            logger.error(f"SSE错误: {e}")
        finally:
            event_manager.remove_subscriber(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/news_trading/status")
async def get_news_trading_status():
    """获取消息交易系统状态和关键指标"""
    try:
        # 计算关键指标
        from news_trading.config import SUPPORTED_COINS
        
        # 总币种数
        total_coins = len(SUPPORTED_COINS)
        
        # 总用户数（活跃的AI模型数）
        total_users = len(news_handler.analyzers) if news_handler.analyzers else 0
        
        # 总交易量和总盈利（从Redis获取历史数据）
        total_volume = 0.0
        total_profit = 0.0
        
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            # 遍历所有AI的交易历史
            if news_handler.analyzers:
                for ai_name in news_handler.analyzers.keys():
                    # 获取该AI的交易历史
                    trades_key = f"news_trades:{ai_name}"
                    trades_data = r.get(trades_key)
                    
                    if trades_data:
                        import json
                        trades = json.loads(trades_data)
                        
                        for trade in trades:
                            # 累加交易量（使用notional value）
                            if 'size' in trade and 'entry_price' in trade:
                                total_volume += abs(float(trade['size']) * float(trade['entry_price']))
                            
                            # 累加盈利（如果有平仓盈利记录）
                            if 'pnl' in trade:
                                total_profit += float(trade['pnl'])
        
        except Exception as redis_error:
            logger.warning(f"⚠️  无法获取Redis交易数据: {redis_error}")
        
        return {
            "running": len(news_listeners) > 0,
            "active_ais": list(news_handler.analyzers.keys()) if news_handler.analyzers else [],
            "listeners": len(news_listeners),
            "metrics": {
                "total_coins": total_coins,
                "total_users": total_users,
                "total_volume": round(total_volume, 2),
                "total_profit": round(total_profit, 2)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ 获取状态失败: {e}", exc_info=True)
        return {
            "running": False,
            "active_ais": [],
            "listeners": 0,
            "metrics": {
                "total_coins": 0,
                "total_users": 0,
                "total_volume": 0.0,
                "total_profit": 0.0
            }
        }


def load_submitted_coins():
    """启动时加载用户提交的币种到SUPPORTED_COINS和COIN_PROFILES"""
    import json
    from news_trading.coin_profiles import COIN_PROFILES, ProjectType, ProjectStage, TradingPlatform, NewsSource
    from news_trading.config import SUPPORTED_COINS
    
    submissions_file = "coin_submissions.json"
    
    try:
        with open(submissions_file, 'r') as f:
            submissions = json.load(f)
        
        if not submissions:
            logger.info("📋 未发现用户提交的币种")
            return
        
        logger.info(f"📋 加载 {len(submissions)} 个用户提交的币种...")
        
        for submission in submissions:
            if submission.get('status') != 'active':
                continue
            
            symbol = submission['symbol'].upper()
            
            # 添加到SUPPORTED_COINS（如果不存在）
            if symbol not in SUPPORTED_COINS:
                SUPPORTED_COINS.append(symbol)
                logger.info(f"  ✅ [{symbol}] 已添加到监控列表")
            
            # 如果COIN_PROFILES中不存在，创建基本配置
            if symbol not in COIN_PROFILES:
                # 简化的配置，避免重复submit_coin_full的逻辑
                COIN_PROFILES[symbol] = {
                    "name": symbol,
                    "full_name": submission.get('name', symbol),
                    "description": f"Community submitted: {submission.get('name', symbol)}",
                    "twitter": submission.get('twitter', ''),
                    "background": {
                        "total_funding": "Community Submission",
                        "track": "Community Token",
                    },
                    "project_type": ProjectType.NORMAL,
                    "current_stage": ProjectStage.ON_CHAIN,
                    "next_stage": ProjectStage.CEX_ALPHA,
                    "stage_progress": {
                        "completed": [],
                        "current": ProjectStage.ON_CHAIN.value,
                        "upcoming": "CEX Listing"
                    },
                    "stage_links": {},
                    "upside_potential": {
                        "market_position": "Community submitted token",
                        "narrative": "User-generated content",
                        "catalysts": ["Community support", "Platform listings"],
                        "risk_factors": ["Community submission - DYOR"],
                        "target_multiplier": "TBD"
                    },
                    "trading_platforms": [TradingPlatform.HYPERLIQUID],
                    "news_sources": [NewsSource.BINANCE_SPOT, NewsSource.BINANCE_FUTURES],
                    "why_monitor": f"Community submitted: {submission.get('name', symbol)}"
                }
                logger.info(f"  ✅ [{symbol}] 已添加到币种配置")
        
        logger.info(f"✅ 已加载用户提交的币种，当前监控: {len(SUPPORTED_COINS)} 个\n")
        
    except FileNotFoundError:
        logger.info("📋 首次启动，未发现coin_submissions.json")
    except json.JSONDecodeError as e:
        logger.error(f"❌ 解析coin_submissions.json失败: {e}")
    except Exception as e:
        logger.error(f"❌ 加载用户提交币种失败: {e}")


async def preload_coin_configs():
    """系统启动时预加载所有监控币种的精度配置（优化首次交易速度）"""
    from news_trading.config import SUPPORTED_COINS
    from trading.precision_config import PrecisionConfig
    import time
    
    logger.info(f"🔄 预加载 {len(SUPPORTED_COINS)} 个币种的精度配置...")
    start_time = time.time()
    success_count = 0
    
    for coin in SUPPORTED_COINS:
        try:
            # 预加载精度配置（会自动缓存）
            precision_config = PrecisionConfig.get_hyperliquid_precision(coin)
            success_count += 1
            logger.info(f"  ✅ [{coin}] 精度配置已缓存")
        except Exception as e:
            logger.warning(f"  ⚠️ [{coin}] 预加载失败: {e}")
    
    total_time = time.time() - start_time
    logger.info(
        f"✅ 精度配置预加载完成: {success_count}/{len(SUPPORTED_COINS)} 成功 "
        f"(耗时: {total_time:.2f}s)"
    )
    logger.info(f"🚀 首次开仓速度预计提升 70% (9s → 2-3s)\n")


# ================== Alpha Hunter API ==================

@app.post("/api/alpha_hunter/approve_agent")
async def approve_agent_for_user(request: dict):
    """
    为用户生成并授权 Agent（调用 Hyperliquid approve_agent）
    
    Expected JSON:
    {
        "user_private_key": "0x...",  # 用户主钱包私钥（仅用于调用 approve_agent）
        "agent_name": "my_alpha_hunter"  # 可选的 Agent 名称
    }
    
    Returns:
    {
        "status": "ok",
        "agent_address": "0x...",
        "agent_private_key": "0x..."  # 返回给前端保存
    }
    """
    try:
        user_private_key = request.get("user_private_key")
        agent_name = request.get("agent_name", "alpha_hunter")
        
        if not user_private_key:
            return {"status": "error", "message": "缺少用户私钥"}
        
        # 创建用户的 Hyperliquid 客户端
        user_client = HyperliquidClient(user_private_key, settings.hyperliquid_testnet)
        
        # 调用 approve_agent
        logger.info(f"🔑 调用 Hyperliquid approve_agent for {agent_name}...")
        approve_result, agent_private_key = await user_client.approve_agent(agent_name)
        
        if approve_result.get("status") != "ok":
            return {
                "status": "error",
                "message": f"Hyperliquid approve_agent 失败: {approve_result}"
            }
        
        # 获取 Agent 地址
        import eth_account
        agent_account = eth_account.Account.from_key(agent_private_key)
        agent_address = agent_account.address
        
        logger.info(f"✅ Agent 授权成功: {agent_address}")
        
        return {
            "status": "ok",
            "agent_address": agent_address,
            "agent_private_key": agent_private_key,
            "user_address": user_client.account.address
        }
        
    except Exception as e:
        logger.error(f"❌ approve_agent_for_user 失败: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/alpha_hunter/register")
async def register_alpha_hunter(request: dict):
    """
    注册 Alpha Hunter 用户（用户已在前端用 MetaMask 签名 EIP-712 approve_agent 消息）
    
    Expected JSON:
    {
        "user_address": "0x...",
        "agent_private_key": "0x...",  # 前端生成的 Agent 私钥
        "agent_address": "0x...",      # 前端推导的 Agent 地址
        "agent_name": "alpha_hunter_BTC",
        "monitored_coins": ["BTC"],
        "margin_per_coin": {"BTC": 100},
        "nonce": 1730295600000,  # 前端生成的 timestamp
        "signature": "0x..."     # MetaMask EIP-712 签名（hex string）
    }
    """
    try:
        user_address = request.get("user_address")
        agent_private_key = request.get("agent_private_key")
        agent_address = request.get("agent_address")
        agent_name = request.get("agent_name", "alpha_hunter")
        monitored_coins = request.get("monitored_coins", [])
        margin_per_coin = request.get("margin_per_coin", {})
        nonce = request.get("nonce")
        signature = request.get("signature")
        
        if not all([user_address, agent_private_key, agent_address, nonce, signature]):
            return {"status": "error", "message": "缺少必要参数"}
        
        logger.info(f"🔐 收到 Alpha Hunter 注册请求:")
        logger.info(f"   用户地址: {user_address}")
        logger.info(f"   Agent地址: {agent_address}")
        logger.info(f"   Agent名称: {agent_name}")
        logger.info(f"   签名: {signature[:20]}...")
        
        # Step 1: 调用 Hyperliquid API 提交 approve_agent 请求
        logger.info(f"📡 Step 1: 提交 approve_agent 到 Hyperliquid API...")
        
        import httpx
        
        # 构造 Hyperliquid approve_agent action
        action = {
            "type": "approveAgent",
            "signatureChainId": "0x66eee",  # Arbitrum One chain ID
            "hyperliquidChain": "Testnet" if settings.hyperliquid_testnet else "Mainnet",
            "agentAddress": agent_address,
            "agentName": agent_name,
            "nonce": nonce
        }
        
        # 解析签名（hex string -> {r, s, v}）
        sig_hex = signature[2:] if signature.startswith('0x') else signature
        sig_r = '0x' + sig_hex[:64]
        sig_s = '0x' + sig_hex[64:128]
        sig_v = int(sig_hex[128:130], 16)
        
        signature_obj = {
            "r": sig_r,
            "s": sig_s,
            "v": sig_v
        }
        
        # 构造 Hyperliquid API 请求
        hyperliquid_url = "https://api.hyperliquid-testnet.xyz/exchange" if settings.hyperliquid_testnet else "https://api.hyperliquid.xyz/exchange"
        
        payload = {
            "action": action,
            "signature": signature_obj,
            "nonce": nonce
        }
        
        logger.info(f"   Hyperliquid URL: {hyperliquid_url}")
        logger.info(f"   Payload: {payload}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(hyperliquid_url, json=payload)
            result = response.json()
        
        logger.info(f"   Response: {result}")
        
        if result.get("status") != "ok":
            return {
                "status": "error",
                "message": f"Hyperliquid approve_agent 失败: {result}"
            }
        
        logger.info(f"✅ Step 1: Hyperliquid approve_agent 成功!")
        
        # Step 2: 注册到本地 Alpha Hunter 系统
        logger.info(f"📝 Step 2: 注册到本地系统...")
        
        result = await alpha_hunter.register_user(
            user_address=user_address,
            agent_private_key=agent_private_key,
            monitored_coins=monitored_coins,
            margin_per_coin=margin_per_coin
        )
        
        logger.info(f"✅ Step 2: 本地注册成功!")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ register_alpha_hunter 失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


@app.post("/api/alpha_hunter/start")
async def start_alpha_hunter(request: dict):
    """开始 Alpha Hunter 监控"""
    try:
        user_address = request.get("user_address")
        if not user_address:
            return {"status": "error", "message": "缺少用户地址"}
        
        result = await alpha_hunter.start_monitoring(user_address)
        return result
        
    except Exception as e:
        logger.error(f"❌ start_alpha_hunter 失败: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/alpha_hunter/stop")
async def stop_alpha_hunter(request: dict):
    """停止 Alpha Hunter 监控"""
    try:
        user_address = request.get("user_address")
        if not user_address:
            return {"status": "error", "message": "缺少用户地址"}
        
        result = await alpha_hunter.stop_monitoring(user_address)
        return result
        
    except Exception as e:
        logger.error(f"❌ stop_alpha_hunter 失败: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/alpha_hunter/status")
async def get_alpha_hunter_status(user_address: str):
    """获取 Alpha Hunter 用户状态"""
    try:
        result = alpha_hunter.get_user_status(user_address)
        return result
        
    except Exception as e:
        logger.error(f"❌ get_alpha_hunter_status 失败: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    logger.info(f"🌐 启动AI共识交易系统 - 多平台对比版")
    logger.info(f"启用平台: {', '.join(get_enabled_platforms())}")
    logger.info(f"⏱️  决策周期: {settings.consensus_interval//60}分钟")
    logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意")
    logger.info(f"🌐 前端页面: http://localhost:{settings.api_port}/")
    
    # 1. 加载用户提交的币种
    load_submitted_coins()
    
    # 2. 预加载币种配置
    import asyncio
    asyncio.run(preload_coin_configs())
    
    # 3. 初始化 Alpha Hunter
    asyncio.run(alpha_hunter.initialize())
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

