"""
交易客户端基类
定义统一的接口，供不同交易平台实现
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseExchangeClient(ABC):
    """交易所客户端基类"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        初始化客户端
        
        Args:
            private_key: 私钥
            testnet: 是否使用测试网
        """
        self.testnet = testnet
        self.address = None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典，包含余额等信息
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, coin: str) -> Dict:
        """
        获取市场数据
        
        Args:
            coin: 币种符号
            
        Returns:
            市场数据字典，包含：
            - coin: 币种
            - price: 当前价格
            - mark_price: 标记价格
            - funding_rate: 资金费率
            - open_interest: 持仓量
            - change_24h: 24小时涨跌幅
            - volume: 24小时成交量
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, coin: str) -> Dict:
        """
        获取订单簿
        
        Args:
            coin: 币种符号
            
        Returns:
            订单簿数据 {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        """
        pass
    
    @abstractmethod
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            coin: 币种符号
            limit: 返回数量
            
        Returns:
            成交记录列表
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False
    ) -> Dict:
        """
        下单
        
        Args:
            coin: 币种符号
            is_buy: 是否买入
            size: 数量
            price: 价格（None表示市价单）
            order_type: 订单类型
            reduce_only: 是否只减仓
            
        Returns:
            订单结果
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, coin: str, order_id: str) -> Dict:
        """
        取消订单
        
        Args:
            coin: 币种符号
            order_id: 订单ID
            
        Returns:
            取消结果
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """
        获取未成交订单
        
        Args:
            coin: 币种符号（可选）
            
        Returns:
            订单列表
        """
        pass
    
    @abstractmethod
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """
        获取用户历史成交记录
        
        Args:
            limit: 返回数量限制
            start_time_ms: 开始时间（毫秒时间戳）
            
        Returns:
            成交记录列表
        """
        pass
    
    @abstractmethod
    async def get_candles(
        self,
        coin: str,
        interval: str = "15m",
        lookback: int = 100,
        timeout: int = 30
    ) -> List[Dict]:
        """
        获取 K 线数据
        
        Args:
            coin: 币种符号
            interval: K线周期
            lookback: 回溯K线数量
            timeout: 超时时间（秒）
            
        Returns:
            K线数据列表 [{"time": timestamp, "open": o, "high": h, "low": l, "close": c, "volume": v}, ...]
        """
        pass
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        pass
    
    async def close_session(self):
        """关闭会话（可选实现）"""
        pass

