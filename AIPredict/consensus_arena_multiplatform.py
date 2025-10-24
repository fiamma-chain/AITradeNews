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

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()


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
        
        # 根据配置初始化各个平台
        enabled_platforms = get_enabled_platforms()
        logger.info(f"[{name}] 启用的交易平台: {enabled_platforms}")
        
        for platform in enabled_platforms:
            if platform == "hyperliquid":
                client = HyperliquidClient(private_key, settings.hyperliquid_testnet)
                self.multi_trader.add_platform(client, f"{name}-Hyperliquid")
            elif platform == "aster":
                client = AsterClient(private_key, settings.aster_testnet)
                self.multi_trader.add_platform(client, f"{name}-Aster")
        
        # 创建用于获取市场数据的 Hyperliquid 客户端（即使不用于交易）
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
        
        # 根据配置初始化各个平台（使用平台级别的 testnet 配置）
        enabled_platforms = get_enabled_platforms()
        logger.info(f"[{name}] 启用的交易平台: {enabled_platforms}")
        
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
        logger.info(f"交易币种: {symbol_filter.get_default_symbol()}")
        logger.info(f"⏱️  决策周期: {self.update_interval//60}分钟")
        logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意才执行")
        logger.info(f"每组初始资金: ${settings.ai_initial_balance}")
        logger.info("=" * 80)
        
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
        try:
            individual_configs = get_individual_traders_config()
        except ValueError as e:
            logger.error(f"\n❌ 独立AI交易者配置错误:")
            logger.error(str(e))
            logger.error("\n请检查 .env 文件中的独立AI交易者私钥配置")
            return False
        
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
                
                # 并行处理所有组
                await asyncio.gather(*[process_group(group) for group in self.groups])
                
                # 并行处理所有独立AI交易者
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
                
                if self.individual_traders:
                    await asyncio.gather(*[process_individual_trader(trader) for trader in self.individual_traders])
                
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
    """根路径"""
    from fastapi.responses import FileResponse
    response = FileResponse("web/consensus_arena.html")
    # 禁用缓存，确保每次都加载最新版本
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.mount("/web", StaticFiles(directory="web"), name="web")


if __name__ == "__main__":
    logger.info(f"🌐 启动AI共识交易系统 - 多平台对比版")
    logger.info(f"启用平台: {', '.join(get_enabled_platforms())}")
    logger.info(f"⏱️  决策周期: {settings.consensus_interval//60}分钟")
    logger.info(f"🎯 共识规则: 每组至少{settings.consensus_min_votes}个AI同意")
    logger.info(f"🌐 前端页面: http://localhost:{settings.api_port}/")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info"
    )

