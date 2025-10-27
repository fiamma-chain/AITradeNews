"""
DEX持仓管理器 - 分批止盈策略
DEX Position Manager with Gradual Take Profit
"""
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class DEXPositionManager:
    """
    DEX持仓管理器
    
    现货分批止盈策略：
    - 20%涨幅: 卖出25%持仓
    - 30%涨幅: 卖出25%持仓（累计50%）
    - 40%涨幅: 卖出25%持仓（累计75%）
    - 50%涨幅: 卖出剩余25%（完全止盈）
    """
    
    def __init__(self, client):
        """
        初始化持仓管理器
        
        Args:
            client: DEX客户端实例
        """
        self.client = client
        self.positions: Dict[str, Dict] = {}  # {coin: position_info}
        
        # 分批止盈配置
        self.take_profit_levels = [
            {"threshold": 0.20, "sell_pct": 0.25, "label": "一批"},  # 20%涨幅，卖25%
            {"threshold": 0.30, "sell_pct": 0.25, "label": "二批"},  # 30%涨幅，卖25%
            {"threshold": 0.40, "sell_pct": 0.25, "label": "三批"},  # 40%涨幅，卖25%
            {"threshold": 0.50, "sell_pct": 0.25, "label": "四批"},  # 50%涨幅，卖25%
        ]
        
        logger.info("📊 DEX持仓管理器初始化")
        logger.info("   分批止盈策略:")
        for level in self.take_profit_levels:
            logger.info(f"      {level['threshold']*100:.0f}%涨幅 -> 卖出{level['sell_pct']*100:.0f}% ({level['label']})")
    
    def add_position(
        self,
        coin: str,
        amount: Decimal,
        entry_price: Decimal,
        cost_usdc: Decimal,
        tx_hash: str = None
    ):
        """
        添加持仓记录
        
        Args:
            coin: 代币符号
            amount: 持仓数量
            entry_price: 入场价格（USDC per token）
            cost_usdc: 成本（USDC）
            tx_hash: 交易哈希
        """
        self.positions[coin] = {
            "coin": coin,
            "total_amount": amount,  # 总持仓
            "remaining_amount": amount,  # 剩余持仓
            "entry_price": entry_price,
            "cost_usdc": cost_usdc,
            "entry_time": datetime.now(),
            "tx_hash": tx_hash,
            "sold_batches": [],  # 已卖出的批次
            "total_profit_usdc": Decimal(0),  # 累计利润
        }
        
        logger.info(
            f"✅ [{coin}] 持仓已记录\n"
            f"   数量: {amount}\n"
            f"   入场价: ${entry_price:.6f}\n"
            f"   成本: ${cost_usdc:.2f}"
        )
    
    async def check_take_profit(self, coin: str, current_price: Decimal) -> List[Dict]:
        """
        检查是否触发止盈
        
        Args:
            coin: 代币符号
            current_price: 当前价格
            
        Returns:
            需要执行的卖出操作列表
        """
        if coin not in self.positions:
            return []
        
        position = self.positions[coin]
        entry_price = position["entry_price"]
        remaining_amount = position["remaining_amount"]
        
        if remaining_amount <= 0:
            logger.info(f"ℹ️  [{coin}] 持仓已全部卖出")
            return []
        
        # 计算涨幅
        profit_pct = (current_price - entry_price) / entry_price
        
        # 检查每个止盈级别
        sell_orders = []
        
        for level in self.take_profit_levels:
            threshold = level["threshold"]
            sell_pct = level["sell_pct"]
            label = level["label"]
            
            # 检查是否已经执行过这个批次
            if any(batch["threshold"] == threshold for batch in position["sold_batches"]):
                continue
            
            # 检查是否达到止盈阈值
            if profit_pct >= threshold:
                # 计算卖出数量（基于总持仓的百分比）
                sell_amount = position["total_amount"] * Decimal(str(sell_pct))
                
                # 确保不超过剩余持仓
                sell_amount = min(sell_amount, remaining_amount)
                
                if sell_amount > 0:
                    sell_orders.append({
                        "coin": coin,
                        "amount": sell_amount,
                        "threshold": threshold,
                        "sell_pct": sell_pct,
                        "label": label,
                        "current_price": current_price,
                        "profit_pct": profit_pct,
                    })
                    
                    logger.info(
                        f"🎯 [{coin}] 触发{label}止盈 ({threshold*100:.0f}%)\n"
                        f"   涨幅: {profit_pct*100:.2f}%\n"
                        f"   入场价: ${entry_price:.6f}\n"
                        f"   当前价: ${current_price:.6f}\n"
                        f"   卖出数量: {sell_amount} ({sell_pct*100:.0f}%总仓位)\n"
                        f"   剩余持仓: {remaining_amount}"
                    )
        
        return sell_orders
    
    async def execute_sell(self, coin: str, sell_order: Dict) -> bool:
        """
        执行卖出操作
        
        Args:
            coin: 代币符号
            sell_order: 卖出订单信息
            
        Returns:
            是否成功
        """
        try:
            amount = sell_order["amount"]
            current_price = sell_order["current_price"]
            
            logger.info(f"🔄 [{coin}] 执行{sell_order['label']}止盈卖出...")
            
            # 执行卖出（使用DEX客户端）
            result = await self.client.place_order(
                coin=coin,
                is_buy=False,  # 卖出
                sz=float(amount),
            )
            
            if result.get("status") != "ok":
                logger.error(f"❌ [{coin}] 卖出失败: {result.get('message')}")
                return False
            
            # 更新持仓
            position = self.positions[coin]
            position["remaining_amount"] -= amount
            
            # 计算这批利润
            entry_price = position["entry_price"]
            profit = amount * (current_price - entry_price)
            position["total_profit_usdc"] += profit
            
            # 记录已卖出批次
            position["sold_batches"].append({
                "threshold": sell_order["threshold"],
                "label": sell_order["label"],
                "amount": amount,
                "price": current_price,
                "profit": profit,
                "time": datetime.now(),
                "tx_hash": result.get("tx_hash"),
            })
            
            logger.info(
                f"✅ [{coin}] {sell_order['label']}止盈完成\n"
                f"   卖出数量: {amount}\n"
                f"   卖出价格: ${current_price:.6f}\n"
                f"   本批利润: ${profit:.2f}\n"
                f"   累计利润: ${position['total_profit_usdc']:.2f}\n"
                f"   剩余持仓: {position['remaining_amount']}\n"
                f"   交易哈希: {result.get('tx_hash')}"
            )
            
            # 如果全部卖出，打印总结
            if position["remaining_amount"] <= 0:
                self._print_position_summary(coin)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [{coin}] 执行卖出异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _print_position_summary(self, coin: str):
        """打印持仓总结"""
        if coin not in self.positions:
            return
        
        position = self.positions[coin]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎊 [{coin}] 完全止盈 - 持仓总结")
        logger.info(f"{'='*60}")
        logger.info(f"入场价格: ${position['entry_price']:.6f}")
        logger.info(f"总成本: ${position['cost_usdc']:.2f}")
        logger.info(f"总持仓: {position['total_amount']}")
        logger.info(f"卖出批次: {len(position['sold_batches'])}批")
        
        for batch in position["sold_batches"]:
            logger.info(
                f"  {batch['label']}: "
                f"{batch['amount']} @ ${batch['price']:.6f} "
                f"= ${batch['profit']:.2f}"
            )
        
        logger.info(f"累计利润: ${position['total_profit_usdc']:.2f}")
        roi = (position['total_profit_usdc'] / position['cost_usdc']) * 100
        logger.info(f"投资回报率: {roi:.2f}%")
        logger.info(f"{'='*60}\n")
    
    def get_position(self, coin: str) -> Optional[Dict]:
        """获取持仓信息"""
        return self.positions.get(coin)
    
    def remove_position(self, coin: str):
        """移除持仓记录"""
        if coin in self.positions:
            del self.positions[coin]
            logger.info(f"🗑️  [{coin}] 持仓记录已清除")
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """获取所有持仓"""
        return self.positions.copy()
    
    async def monitor_positions(self, get_price_func) -> List[Dict]:
        """
        监控所有持仓的止盈
        
        Args:
            get_price_func: 获取价格的函数 async def get_price(coin: str) -> Decimal
            
        Returns:
            执行的卖出操作列表
        """
        executed_sells = []
        
        for coin in list(self.positions.keys()):
            try:
                # 获取当前价格
                current_price = await get_price_func(coin)
                
                # 检查止盈
                sell_orders = await self.check_take_profit(coin, current_price)
                
                # 执行卖出
                for sell_order in sell_orders:
                    success = await self.execute_sell(coin, sell_order)
                    if success:
                        executed_sells.append({
                            "coin": coin,
                            "order": sell_order,
                        })
            
            except Exception as e:
                logger.error(f"❌ [{coin}] 监控持仓时出错: {e}")
        
        return executed_sells

