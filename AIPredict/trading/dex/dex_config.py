"""
DEX配置文件
DEX Configuration
"""
from typing import Dict, List
from enum import Enum


class Chain(Enum):
    """支持的区块链"""
    BASE = "base"
    BSC = "bsc"
    ETHEREUM = "ethereum"


class DEXProtocol(Enum):
    """支持的DEX协议"""
    UNISWAP_V4 = "uniswap_v4"
    PANCAKESWAP = "pancakeswap"


# ===== Base链配置 =====
BASE_CONFIG = {
    "chain_id": 8453,
    "rpc_url": "https://mainnet.base.org",
    "explorer": "https://basescan.org",
    "native_token": "ETH",
    "wrapped_native": "0x4200000000000000000000000000000000000006",  # WETH on Base
    
    # Uniswap V3/V4合约（Base链使用V3路由）
    "uniswap_v4": {
        "pool_manager": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",  # V3 Factory
        "swap_router": "0x2626664c2603336E57B271c5C0b26F421741e481",  # SwapRouter02
        "quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",  # QuoterV2
    }
}

# ===== BSC链配置 =====
BSC_CONFIG = {
    "chain_id": 56,
    "rpc_url": "https://bsc-dataseed.binance.org/",
    "explorer": "https://bscscan.com",
    "native_token": "BNB",
    "wrapped_native": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    
    # PancakeSwap合约
    "pancakeswap": {
        "router_v3": "0x1b81D678ffb9C0263b24A97847620C99d213eB14",
        "factory": "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865",
        "quoter": "0xB048Bbc1Ee6b733FFfCFb9e9CeF7375518e25997",
    }
}

# ===== 代币配置 =====

# Base链代币
BASE_TOKENS: Dict[str, Dict] = {
    "PING": {
        "name": "Ping",
        "address": "0xd85c31854c2b0fb40aaa9e2fc4da23c21f829d46",
        "decimals": 18,
        "chain": "base",
        "dex": "uniswap_v4",
        "base_pair": "USDC",  # 交易对
    },
    "USDC": {
        "name": "USD Coin",
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "decimals": 6,
        "chain": "base",
        "is_stablecoin": True,
    },
    "WETH": {
        "name": "Wrapped Ether",
        "address": "0x4200000000000000000000000000000000000006",
        "decimals": 18,
        "chain": "base",
    },
}

# BSC链代币
BSC_TOKENS: Dict[str, Dict] = {
    "USDT": {
        "name": "Tether USD",
        "address": "0x55d398326f99059fF775485246999027B3197955",
        "decimals": 18,
        "chain": "bsc",
        "is_stablecoin": True,
    },
    "WBNB": {
        "name": "Wrapped BNB",
        "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "decimals": 18,
        "chain": "bsc",
    },
    "BUSD": {
        "name": "Binance USD",
        "address": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
        "decimals": 18,
        "chain": "bsc",
        "is_stablecoin": True,
    },
}

# 所有代币
ALL_DEX_TOKENS = {**BASE_TOKENS, **BSC_TOKENS}


# ===== DEX交易配置 =====
DEX_TRADING_CONFIG = {
    # 滑点配置
    "max_slippage": 0.01,  # 1%最大滑点
    "default_slippage": 0.005,  # 0.5%默认滑点
    
    # 交易截止时间
    "deadline_seconds": 300,  # 5分钟
    
    # Gas配置
    "gas_limit_swap": 500000,  # Swap交易Gas限制
    "gas_price_multiplier": 1.1,  # Gas价格倍数（加速交易）
    
    # 最小流动性要求
    "min_liquidity_usd": 10000,  # 最小池子流动性$10,000
    
    # 交易限制
    "max_position_size_usd": 5000,  # 单笔最大交易$5,000
    "min_position_size_usd": 10,  # 单笔最小交易$10
}


def get_chain_config(chain: str) -> Dict:
    """获取链配置"""
    if chain.lower() == "base":
        return BASE_CONFIG
    elif chain.lower() == "bsc":
        return BSC_CONFIG
    else:
        raise ValueError(f"Unsupported chain: {chain}")


def get_token_config(symbol: str) -> Dict:
    """获取代币配置"""
    symbol = symbol.upper()
    if symbol in ALL_DEX_TOKENS:
        return ALL_DEX_TOKENS[symbol]
    raise ValueError(f"Token {symbol} not configured")


def is_dex_token(symbol: str) -> bool:
    """检查是否为DEX代币"""
    return symbol.upper() in ALL_DEX_TOKENS


def get_token_chain(symbol: str) -> str:
    """获取代币所在链"""
    config = get_token_config(symbol)
    return config["chain"]


def get_stablecoin_for_chain(chain: str) -> str:
    """获取链上的稳定币"""
    if chain.lower() == "base":
        return "USDC"
    elif chain.lower() == "bsc":
        return "USDT"
    else:
        raise ValueError(f"No stablecoin configured for chain: {chain}")


def get_supported_dex_tokens() -> List[str]:
    """获取所有支持的DEX代币列表"""
    return list(ALL_DEX_TOKENS.keys())

