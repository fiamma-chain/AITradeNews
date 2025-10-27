"""
PancakeSwap客户端 - BSC链
PancakeSwap Client for BSC Chain
"""
import asyncio
import time
from decimal import Decimal
from typing import Dict, Optional, List
from web3 import Web3
from eth_account import Account
import logging

from .base_dex_client import BaseDEXClient
from .dex_config import BSC_CONFIG, BSC_TOKENS, DEX_TRADING_CONFIG

logger = logging.getLogger(__name__)


# ERC20 ABI（复用Uniswap的）
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

# PancakeSwap V3 SwapRouter ABI（简化版）
PANCAKE_SWAP_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct IV3SwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
]


class PancakeSwapClient(BaseDEXClient):
    """PancakeSwap客户端（BSC链）"""
    
    def __init__(self, private_key: str, rpc_url: str = None):
        """
        初始化PancakeSwap客户端
        
        Args:
            private_key: 私钥
            rpc_url: RPC URL，默认使用BSC主网
        """
        rpc_url = rpc_url or BSC_CONFIG["rpc_url"]
        super().__init__("bsc", private_key, rpc_url)
        
        # 初始化Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # 加载账户
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # PancakeSwap配置
        self.router_address = BSC_CONFIG["pancakeswap"]["router_v3"]
        self.router_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.router_address),
            abi=PANCAKE_SWAP_ROUTER_ABI
        )
        
        # 代币配置
        self.tokens = BSC_TOKENS
        
        # 交易配置
        self.max_slippage = DEX_TRADING_CONFIG["max_slippage"]
        self.deadline_seconds = DEX_TRADING_CONFIG["deadline_seconds"]
        
        logger.info(f"✅ PancakeSwap客户端初始化成功")
        logger.info(f"   地址: {self.address}")
        logger.info(f"   链: BSC ({BSC_CONFIG['chain_id']})")
        logger.info(f"   RPC: {rpc_url}")
    
    async def get_account_info(self) -> Dict:
        """获取账户信息"""
        try:
            # 获取BNB余额
            bnb_balance = self.w3.eth.get_balance(self.address)
            bnb_balance_decimal = Decimal(bnb_balance) / Decimal(10**18)
            
            # 获取USDT余额（BSC链稳定币）
            usdt_balance = await self.get_token_balance(self.tokens["USDT"]["address"])
            
            return {
                "address": self.address,
                "chain": "bsc",
                "bnb_balance": float(bnb_balance_decimal),
                "usdt_balance": float(usdt_balance),
                "withdrawable": float(usdt_balance),  # 兼容CEX接口
            }
        except Exception as e:
            logger.error(f"❌ 获取账户信息失败: {e}")
            return {
                "address": self.address,
                "withdrawable": 0.0,
            }
    
    async def get_token_balance(self, token_address: str) -> Decimal:
        """获取代币余额"""
        try:
            token_address = self.w3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            balance = token_contract.functions.balanceOf(self.address).call()
            decimals = token_contract.functions.decimals().call()
            
            return Decimal(balance) / Decimal(10**decimals)
        except Exception as e:
            logger.error(f"❌ 获取代币余额失败 {token_address}: {e}")
            return Decimal(0)
    
    async def get_token_price(self, token_address: str) -> Decimal:
        """
        获取代币价格（相对于USDT）
        
        注意：这是一个简化实现，实际应该查询PancakeSwap池子
        """
        # TODO: 实现从PancakeSwap池子获取实时价格
        logger.warning("⚠️ get_token_price 使用模拟实现")
        return Decimal("0.001")  # 模拟价格
    
    async def approve_token(self, token_address: str, spender: str, amount: int = None):
        """
        授权代币给spender
        
        Args:
            token_address: 代币地址
            spender: 授权对象地址
            amount: 授权数量，None表示无限授权
        """
        try:
            token_address = self.w3.to_checksum_address(token_address)
            spender = self.w3.to_checksum_address(spender)
            token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            
            # 检查当前授权额度
            current_allowance = token_contract.functions.allowance(
                self.address, spender
            ).call()
            
            # 如果已经有足够的授权，跳过
            if amount and current_allowance >= amount:
                logger.info(f"✅ 代币已有足够授权: {current_allowance}")
                return True
            
            # 无限授权
            if amount is None:
                amount = 2**256 - 1
            
            # 构建授权交易
            approve_txn = token_contract.functions.approve(spender, amount).build_transaction({
                'from': self.address,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address),
            })
            
            # 签名并发送
            signed_txn = self.account.sign_transaction(approve_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"📤 授权交易已发送: {tx_hash.hex()}")
            
            # 等待确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"✅ 授权成功")
                return True
            else:
                logger.error(f"❌ 授权失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 授权代币失败: {e}")
            return False
    
    async def swap_tokens(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> Dict:
        """
        交换代币（PancakeSwap V3）
        
        Args:
            token_in: 输入代币地址
            token_out: 输出代币地址
            amount_in: 输入数量
            min_amount_out: 最小输出数量
            deadline: 截止时间
            
        Returns:
            交易结果
        """
        try:
            token_in = self.w3.to_checksum_address(token_in)
            token_out = self.w3.to_checksum_address(token_out)
            
            # 转换为整数（考虑decimals）
            # 假设USDT是18位，其他是18位
            amount_in_wei = int(amount_in * Decimal(10**18))  # USDT on BSC
            min_amount_out_wei = int(min_amount_out * Decimal(10**18))  # 目标代币
            
            logger.info(f"🔄 准备Swap (PancakeSwap):")
            logger.info(f"   输入: {amount_in} ({token_in})")
            logger.info(f"   输出: >= {min_amount_out} ({token_out})")
            
            # 1. 授权代币
            logger.info(f"📝 检查授权...")
            approved = await self.approve_token(token_in, self.router_address, amount_in_wei)
            if not approved:
                return {"status": "error", "message": "Token approval failed"}
            
            # 2. 构建swap参数
            swap_params = {
                'tokenIn': token_in,
                'tokenOut': token_out,
                'fee': 2500,  # 0.25% fee tier (PancakeSwap默认)
                'recipient': self.address,
                'amountIn': amount_in_wei,
                'amountOutMinimum': min_amount_out_wei,
                'sqrtPriceLimitX96': 0,  # 无价格限制
            }
            
            # 3. 构建交易
            swap_txn = self.router_contract.functions.exactInputSingle(
                swap_params
            ).build_transaction({
                'from': self.address,
                'gas': DEX_TRADING_CONFIG["gas_limit_swap"],
                'gasPrice': int(self.w3.eth.gas_price * DEX_TRADING_CONFIG["gas_price_multiplier"]),
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'value': 0,
            })
            
            # 4. 签名并发送
            signed_txn = self.account.sign_transaction(swap_txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"📤 Swap交易已发送: {tx_hash.hex()}")
            logger.info(f"   Explorer: {BSC_CONFIG['explorer']}/tx/{tx_hash.hex()}")
            
            # 5. 等待确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt['status'] == 1:
                logger.info(f"✅ Swap成功")
                logger.info(f"   Gas Used: {receipt['gasUsed']}")
                
                return {
                    "status": "ok",
                    "tx_hash": tx_hash.hex(),
                    "gas_used": receipt['gasUsed'],
                    "block_number": receipt['blockNumber'],
                }
            else:
                logger.error(f"❌ Swap失败")
                return {
                    "status": "error",
                    "message": "Transaction reverted",
                    "tx_hash": tx_hash.hex(),
                }
                
        except Exception as e:
            logger.error(f"❌ Swap交易失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e),
            }
    
    async def get_positions(self) -> List[Dict]:
        """
        获取持仓列表
        
        对于DEX现货，"持仓"就是代币余额
        """
        positions = []
        
        for symbol, config in self.tokens.items():
            if config.get("is_stablecoin"):
                continue  # 跳过稳定币
                
            try:
                balance = await self.get_token_balance(config["address"])
                if balance > 0:
                    positions.append({
                        "coin": symbol,
                        "balance": float(balance),
                        "chain": "bsc",
                        "dex": "pancakeswap",
                    })
            except Exception as e:
                logger.error(f"获取{symbol}余额失败: {e}")
        
        return positions
    
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
        
        对于DEX，将订单转换为swap操作
        """
        try:
            logger.info(f"📋 DEX下单 (PancakeSwap): {coin}")
            logger.info(f"   方向: {'买入' if is_buy else '卖出'}")
            logger.info(f"   数量: {sz}")
            
            # 获取代币配置
            if coin.upper() not in self.tokens:
                return {"status": "error", "message": f"Token {coin} not supported"}
            
            token_config = self.tokens[coin.upper()]
            token_address = token_config["address"]
            
            # 获取稳定币配置（BSC使用USDT）
            stablecoin = self.tokens["USDT"]
            stablecoin_address = stablecoin["address"]
            
            if is_buy:
                # 买入：USDT -> Token
                amount_in = Decimal(str(sz))
                min_amount_out = amount_in * Decimal(str(1 - self.max_slippage))
                
                result = await self.swap_tokens(
                    token_in=stablecoin_address,
                    token_out=token_address,
                    amount_in=amount_in,
                    min_amount_out=min_amount_out,
                    deadline=int(time.time()) + self.deadline_seconds
                )
            else:
                # 卖出：Token -> USDT
                amount_in = Decimal(str(sz))
                min_amount_out = amount_in * Decimal(str(1 - self.max_slippage))
                
                result = await self.swap_tokens(
                    token_in=token_address,
                    token_out=stablecoin_address,
                    amount_in=amount_in,
                    min_amount_out=min_amount_out,
                    deadline=int(time.time()) + self.deadline_seconds
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ DEX下单失败: {e}")
            return {"status": "error", "message": str(e)}

