"""
DEX交易客户端基类
Base DEX Trading Client
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from decimal import Decimal


class BaseDEXClient(ABC):
    """DEX交易客户端基类"""
    
    def __init__(self, chain: str, private_key: str, rpc_url: str):
        """
        初始化DEX客户端
        
        Args:
            chain: 链名称 (base, bsc等)
            private_key: 私钥
            rpc_url: RPC节点URL
        """
        self.chain = chain
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.platform_name = f"DEX_{chain.upper()}"
    
    @abstractmethod
    async def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典，包含余额等
        """
        pass
    
    @abstractmethod
    async def get_token_balance(self, token_address: str) -> Decimal:
        """
        获取代币余额
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            代币余额
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str) -> Decimal:
        """
        获取代币价格（相对于USD或稳定币）
        
        Args:
            token_address: 代币合约地址
            
        Returns:
            代币价格
        """
        pass
    
    @abstractmethod
    async def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> Dict:
        """
        交换代币
        
        Args:
            token_in: 输入代币地址
            token_out: 输出代币地址
            amount_in: 输入数量
            min_amount_out: 最小输出数量（滑点保护）
            deadline: 交易截止时间（Unix时间戳）
            
        Returns:
            交易结果
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """
        获取持仓列表
        
        Returns:
            持仓列表
        """
        pass
    
    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: Optional[float] = None,
        reduce_only: bool = False,
        **kwargs
    ) -> Dict:
        """
        下单（统一接口，兼容CEX）
        
        对于DEX，这会转换为swap操作
        """
        # 待实现：将CEX风格的订单转换为DEX的swap
        raise NotImplementedError("DEX place_order needs implementation")

