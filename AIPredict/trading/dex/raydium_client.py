"""
Raydium DEX客户端 (Solana)
Raydium DEX Client
"""
import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional, List
from .base_dex_client import BaseDEXClient
from .dex_config import SOLANA_CONFIG, get_token_config, DEX_TRADING_CONFIG

logger = logging.getLogger(__name__)


class RaydiumClient(BaseDEXClient):
    """Raydium DEX交易客户端 (Solana链)"""
    
    def __init__(self, private_key: str, rpc_url: Optional[str] = None):
        """
        初始化Raydium客户端
        
        Args:
            private_key: Solana钱包私钥 (base58格式)
            rpc_url: Solana RPC节点URL (可选)
        """
        rpc_url = rpc_url or SOLANA_CONFIG["rpc_url"]
        super().__init__("solana", private_key, rpc_url)
        
        self.platform_name = "Raydium"
        
        # Raydium程序地址
        self.amm_program = SOLANA_CONFIG["raydium"]["amm_program"]
        self.serum_program = SOLANA_CONFIG["raydium"]["serum_program"]
        
        # 初始化Solana客户端
        try:
            from solana.rpc.async_api import AsyncClient
            from solders.keypair import Keypair  # type: ignore
            import base58
            
            self.client = AsyncClient(self.rpc_url)
            
            # 解析私钥
            try:
                # 尝试base58格式
                private_key_bytes = base58.b58decode(private_key)
                self.keypair = Keypair.from_bytes(private_key_bytes)
            except Exception:
                # 尝试hex格式
                private_key_bytes = bytes.fromhex(private_key)
                self.keypair = Keypair.from_bytes(private_key_bytes)
            
            self.wallet_address = str(self.keypair.pubkey())
            logger.info(f"✅ Raydium客户端初始化成功 - 钱包: {self.wallet_address[:8]}...")
            
        except ImportError as e:
            logger.error(f"❌ 缺少Solana依赖库: {e}")
            logger.error("请安装: pip install solana solders anchorpy")
            raise
        except Exception as e:
            logger.error(f"❌ Raydium客户端初始化失败: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典，包含SOL余额
        """
        try:
            from solders.pubkey import Pubkey  # type: ignore
            
            # 获取SOL余额
            balance_response = await self.client.get_balance(Pubkey.from_string(self.wallet_address))
            sol_balance = Decimal(balance_response.value) / Decimal(10**9)  # lamports to SOL
            
            return {
                "wallet_address": self.wallet_address,
                "chain": "solana",
                "balance": {
                    "SOL": float(sol_balance)
                },
                "platform": "Raydium"
            }
        except Exception as e:
            logger.error(f"❌ 获取Solana账户信息失败: {e}")
            raise
    
    async def get_token_balance(self, token_address: str) -> Decimal:
        """
        获取SPL代币余额
        
        Args:
            token_address: SPL代币Mint地址
            
        Returns:
            代币余额
        """
        try:
            from solders.pubkey import Pubkey  # type: ignore
            from spl.token.instructions import get_associated_token_address
            
            mint_pubkey = Pubkey.from_string(token_address)
            wallet_pubkey = Pubkey.from_string(self.wallet_address)
            
            # 获取关联代币账户地址
            token_account = get_associated_token_address(wallet_pubkey, mint_pubkey)
            
            # 查询余额
            response = await self.client.get_token_account_balance(token_account)
            
            if response.value is None:
                return Decimal(0)
            
            amount = Decimal(response.value.amount)
            decimals = response.value.decimals
            
            return amount / Decimal(10 ** decimals)
            
        except Exception as e:
            logger.warning(f"⚠️ 获取代币余额失败 {token_address[:8]}...: {e}")
            return Decimal(0)
    
    async def get_token_price(self, token_address: str) -> Decimal:
        """
        获取代币价格（通过Raydium池子）
        
        Args:
            token_address: 代币Mint地址
            
        Returns:
            代币价格（USD）
        """
        try:
            # TODO: 实现从Raydium池子获取实时价格
            # 可以通过查询Raydium AMM池子状态来计算价格
            logger.warning(f"⚠️ Raydium价格查询功能待实现: {token_address}")
            return Decimal(0)
        except Exception as e:
            logger.error(f"❌ 获取代币价格失败: {e}")
            return Decimal(0)
    
    async def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> Dict:
        """
        通过Raydium交换代币
        
        Args:
            token_in: 输入代币Mint地址
            token_out: 输出代币Mint地址
            amount_in: 输入数量
            min_amount_out: 最小输出数量（滑点保护）
            deadline: 交易截止时间
            
        Returns:
            交易结果
        """
        try:
            logger.info(f"🔄 Raydium Swap: {amount_in} {token_in[:8]}... → {token_out[:8]}...")
            
            # TODO: 实现Raydium swap交易
            # 1. 查找对应的AMM池子
            # 2. 构建swap指令
            # 3. 发送交易并等待确认
            
            logger.warning("⚠️ Raydium swap功能待实现")
            
            return {
                "success": False,
                "message": "Raydium swap功能待实现",
                "tx_hash": None
            }
            
        except Exception as e:
            logger.error(f"❌ Raydium swap失败: {e}")
            raise
    
    async def get_positions(self) -> List[Dict]:
        """
        获取持仓列表（Raydium上的代币持仓）
        
        Returns:
            持仓列表
        """
        try:
            # 获取所有SPL代币账户
            from solders.pubkey import Pubkey  # type: ignore
            
            wallet_pubkey = Pubkey.from_string(self.wallet_address)
            
            # TODO: 查询钱包所有代币账户
            # 可以通过getProgramAccounts或getTokenAccountsByOwner实现
            
            logger.warning("⚠️ Raydium持仓查询功能待实现")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 获取Raydium持仓失败: {e}")
            return []
    
    async def close(self):
        """关闭客户端连接"""
        try:
            if hasattr(self, 'client'):
                await self.client.close()
        except Exception as e:
            logger.error(f"❌ 关闭Raydium客户端失败: {e}")


def create_raydium_client(private_key: str, rpc_url: Optional[str] = None) -> RaydiumClient:
    """
    创建Raydium客户端
    
    Args:
        private_key: Solana钱包私钥
        rpc_url: RPC节点URL（可选）
        
    Returns:
        RaydiumClient实例
    """
    return RaydiumClient(private_key, rpc_url)

