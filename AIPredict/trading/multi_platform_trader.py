"""
多平台交易管理器
同时管理多个交易平台，执行相同的交易决策并对比收益
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from ai_models.base_ai import TradingDecision
from trading.base_client import BaseExchangeClient
from trading.auto_trader import AutoTrader
from utils.redis_manager import redis_manager

logger = logging.getLogger(__name__)


class PlatformTrader:
    """单个平台的交易器"""
    
    def __init__(self, client: BaseExchangeClient, name: str):
        """
        初始化平台交易器
        
        Args:
            client: 交易客户端
            name: 平台名称
        """
        self.client = client
        self.name = name
        self.auto_trader = AutoTrader(client)
        self.start_balance = 0.0
        self.stats = {
            "platform": client.platform_name,
            "name": name,
            "balance": 0.0,
            "initial_balance": 0.0,
            "pnl": 0.0,
            "roi": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
            "trades": [],
            "positions": {}
        }
    
    async def initialize(self, initial_balance: float = None, group_name: str = ""):
        """
        初始化平台交易器
        
        Args:
            initial_balance: 初始余额（如果为None，则从账户获取）
            group_name: 组名（用于从Redis恢复交易记录）
        """
        if initial_balance is not None:
            self.start_balance = initial_balance
        else:
            # 从账户获取当前余额
            account = await self.client.get_account_info()
            self.start_balance = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        self.stats["balance"] = self.start_balance
        self.stats["initial_balance"] = self.start_balance
        logger.info(f"[{self.name}] 初始余额: ${self.start_balance:,.2f}")
        
        # 从Redis恢复历史交易记录
        if group_name and redis_manager.is_connected():
            try:
                historical_trades = redis_manager.get_trades(group_name, self.name)
                if historical_trades:
                    self.stats["trades"] = historical_trades
                    logger.info(f"[{self.name}] 📚 从Redis恢复 {len(historical_trades)} 笔历史交易记录")
            except Exception as e:
                logger.error(f"[{self.name}] ❌ 恢复历史交易记录失败: {e}")
    
    async def execute_decision(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        current_price: float,
        group_name: str = ""
    ) -> Optional[Dict]:
        """
        执行交易决策
        
        Args:
            coin: 币种
            decision: 决策
            confidence: 信心度
            reasoning: 理由
            current_price: 当前价格
            group_name: 组名（用于保存到Redis）
            
        Returns:
            交易结果
        """
        # 获取当前余额
        account = await self.client.get_account_info()
        balance = float(account.get('marginSummary', {}).get('accountValue', 0))
        
        # 执行决策
        result = await self.auto_trader.execute_decision(
            coin, decision, confidence, reasoning, current_price, balance
        )
        
        # 更新统计
        if result:
            trade_record = {
                **result,
                "platform": self.client.platform_name
            }
            self.stats["trades"].append(trade_record)
            self.stats["total_trades"] = len([t for t in self.stats["trades"] if t.get('action') == 'close'])
            
            # 保存到Redis（如果是完整交易，即包含px和action）
            if group_name and redis_manager.is_connected() and 'px' in result:
                try:
                    redis_manager.save_trade(group_name, self.name, trade_record)
                except Exception as e:
                    logger.error(f"[{self.name}] ❌ 保存交易到Redis失败: {e}")
        
        return result
    
    async def update_stats(self):
        """更新统计数据"""
        try:
            # 获取当前余额
            account = await self.client.get_account_info()
            current_balance = float(account.get('marginSummary', {}).get('accountValue', 0))
            
            self.stats["balance"] = current_balance
            self.stats["pnl"] = current_balance - self.start_balance
            self.stats["roi"] = (self.stats["pnl"] / self.start_balance * 100) if self.start_balance > 0 else 0
            self.stats["positions"] = self.auto_trader.get_all_positions()
            
            # 计算胜率
            closed_trades = [t for t in self.stats["trades"] if t.get('action') == 'close']
            if closed_trades:
                winning_trades = sum(1 for t in closed_trades if t.get('pnl', 0) > 0)
                self.stats["win_rate"] = (winning_trades / len(closed_trades) * 100)
            
        except Exception as e:
            logger.error(f"[{self.name}] 更新统计失败: {e}")


class MultiPlatformTrader:
    """多平台交易管理器"""
    
    def __init__(self):
        """初始化多平台交易管理器"""
        self.platform_traders: Dict[str, PlatformTrader] = {}
        self.decision_history: List[Dict] = []
    
    def add_platform(self, client: BaseExchangeClient, name: str = None):
        """
        添加交易平台
        
        Args:
            client: 交易客户端
            name: 平台名称（如果为None，使用client.platform_name）
        """
        platform_name = name or client.platform_name
        trader = PlatformTrader(client, platform_name)
        self.platform_traders[platform_name] = trader
        logger.info(f"✅ 添加交易平台: {platform_name}")
    
    async def initialize_all(self, initial_balance: float = None, group_name: str = ""):
        """
        初始化所有平台
        
        Args:
            initial_balance: 初始余额（如果为None，则从各平台账户获取）
            group_name: 组名（用于从Redis恢复数据）
        """
        for name, trader in self.platform_traders.items():
            await trader.initialize(initial_balance, group_name)
    
    async def execute_decision_all(
        self,
        coin: str,
        decision: TradingDecision,
        confidence: float,
        reasoning: str,
        current_price: float,
        group_name: str = ""
    ) -> Dict[str, Optional[Dict]]:
        """
        在所有平台上执行相同的交易决策
        
        Args:
            coin: 币种
            decision: 决策
            confidence: 信心度
            reasoning: 理由
            current_price: 当前价格
            group_name: 组名（用于保存到Redis）
            
        Returns:
            各平台的交易结果字典
        """
        results = {}
        
        # 记录决策
        decision_record = {
            "time": datetime.now().isoformat(),
            "coin": coin,
            "decision": str(decision),
            "confidence": confidence,
            "reasoning": reasoning,
            "price": current_price,
            "results": {}
        }
        
        # 并行执行（可选：也可以顺序执行）
        import asyncio
        tasks = []
        for name, trader in self.platform_traders.items():
            tasks.append(trader.execute_decision(coin, decision, confidence, reasoning, current_price, group_name))
        
        platform_results = await asyncio.gather(*tasks)
        
        # 组合结果
        for (name, trader), result in zip(self.platform_traders.items(), platform_results):
            results[name] = result
            decision_record["results"][name] = result
        
        self.decision_history.append(decision_record)
        
        return results
    
    async def update_all_stats(self):
        """更新所有平台的统计数据"""
        for trader in self.platform_traders.values():
            await trader.update_stats()
    
    def get_comparison_stats(self) -> Dict:
        """
        获取各平台对比统计
        
        Returns:
            对比统计字典
        """
        comparison = {
            "platforms": [],
            "summary": {
                "total_decisions": len(self.decision_history),
                "best_platform": None,
                "worst_platform": None,
                "avg_roi": 0.0
            }
        }
        
        # 收集各平台数据
        platform_data = []
        for name, trader in self.platform_traders.items():
            stats = trader.stats.copy()
            platform_data.append(stats)
            comparison["platforms"].append(stats)
        
        # 计算最佳/最差平台
        if platform_data:
            sorted_by_roi = sorted(platform_data, key=lambda x: x["roi"], reverse=True)
            comparison["summary"]["best_platform"] = sorted_by_roi[0]["name"]
            comparison["summary"]["worst_platform"] = sorted_by_roi[-1]["name"]
            comparison["summary"]["avg_roi"] = sum(p["roi"] for p in platform_data) / len(platform_data)
        
        return comparison
    
    def get_platform_trader(self, name: str) -> Optional[PlatformTrader]:
        """获取指定平台的交易器"""
        return self.platform_traders.get(name)
    
    def get_all_traders(self) -> Dict[str, PlatformTrader]:
        """获取所有平台交易器"""
        return self.platform_traders

