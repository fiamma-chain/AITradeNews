"""
币种配置档案
为每个监控的币种提供详细信息
"""
from typing import Dict, List
from enum import Enum


class TradingPlatform(Enum):
    """交易平台"""
    HYPERLIQUID = "Hyperliquid"
    ASTER = "Aster"
    UNISWAP_V4 = "Uniswap V4 (Base)"
    PANCAKESWAP = "PancakeSwap (BSC)"


class NewsSource(Enum):
    """消息来源"""
    BINANCE_SPOT = "Binance Spot Listing"
    BINANCE_FUTURES = "Binance Futures Listing"
    BINANCE_ALPHA = "Binance Alpha Project"
    UPBIT = "Upbit Listing"
    USER_SUBMIT = "User Submission"


# 币种配置档案
COIN_PROFILES: Dict[str, Dict] = {
    "MON": {
        "name": "Monad",
        "full_name": "Monad Blockchain",
        "description": "High-performance Layer-1 blockchain with parallel execution",
        
        "background": {
            "category": "Layer-1 Blockchain",
            "launch_date": "2024",
            "team": "Former Jump Trading engineers",
            "funding": "$225M Series A (Paradigm lead)",
            "key_features": [
                "10,000 TPS performance",
                "EVM-compatible with parallel execution",
                "MonadBFT consensus mechanism",
                "Backed by top-tier VCs"
            ]
        },
        
        "upside_potential": {
            "market_position": "Next-gen Layer-1 competitor to Solana/Ethereum",
            "narrative": "High-performance blockchain narrative",
            "catalysts": [
                "Mainnet launch expected 2024",
                "Major exchange listings",
                "Growing developer ecosystem",
                "Institutional backing"
            ],
            "risk_factors": [
                "Not yet launched mainnet",
                "Competitive L1 market",
                "Execution risk"
            ],
            "target_multiplier": "5-10x from listing price"
        },
        
        "trading_platforms": [
            TradingPlatform.HYPERLIQUID,
            TradingPlatform.ASTER
        ],
        
        "news_sources": [
            NewsSource.BINANCE_SPOT,
            NewsSource.BINANCE_FUTURES,
            NewsSource.UPBIT,
            NewsSource.USER_SUBMIT
        ],
        
        "why_monitor": "High-profile Layer-1 with strong VC backing and technical innovation. Listing events can trigger significant price movements."
    },
    
    "MEGA": {
        "name": "MegaETH",
        "full_name": "MegaETH Layer-2",
        "description": "Ultra-high-speed Ethereum Layer-2 solution",
        
        "background": {
            "category": "Layer-2 Scaling",
            "launch_date": "2024",
            "team": "Ethereum Foundation alumni",
            "funding": "$20M Seed (Dragonfly, Vitalik)",
            "key_features": [
                "100,000 TPS real-time processing",
                "EVM-equivalent compatibility",
                "Ethereum security inheritance",
                "Real-time blockchain innovation"
            ]
        },
        
        "upside_potential": {
            "market_position": "Next-generation Ethereum L2",
            "narrative": "Real-time blockchain + Ethereum scaling",
            "catalysts": [
                "Testnet/Mainnet milestones",
                "Major exchange listings",
                "Ethereum ecosystem integration",
                "Vitalik endorsement effect"
            ],
            "risk_factors": [
                "Early-stage project",
                "L2 competition (Arbitrum, Optimism, Base)",
                "Technical complexity"
            ],
            "target_multiplier": "3-8x from listing price"
        },
        
        "trading_platforms": [
            TradingPlatform.HYPERLIQUID,
            TradingPlatform.ASTER
        ],
        
        "news_sources": [
            NewsSource.BINANCE_SPOT,
            NewsSource.BINANCE_FUTURES,
            NewsSource.UPBIT,
            NewsSource.USER_SUBMIT
        ],
        
        "why_monitor": "Innovative L2 with Vitalik backing. High-speed narrative + Ethereum ecosystem = strong listing pump potential."
    },
    
    "PING": {
        "name": "PING",
        "full_name": "Ping Token",
        "description": "Community-driven meme token on Base chain",
        
        "background": {
            "category": "Meme Token",
            "launch_date": "2024",
            "chain": "Base (Coinbase L2)",
            "liquidity": "Uniswap V4 DEX",
            "key_features": [
                "Fair launch (no presale)",
                "Community-driven",
                "Base chain native",
                "Low market cap / high volatility"
            ]
        },
        
        "upside_potential": {
            "market_position": "Emerging Base chain meme",
            "narrative": "Meme season + Base ecosystem growth",
            "catalysts": [
                "Community growth",
                "Social media viral moments",
                "CEX listing rumors",
                "Base chain adoption"
            ],
            "risk_factors": [
                "Extreme volatility",
                "No fundamental value",
                "Rug pull risk (check contract)",
                "Liquidity constraints"
            ],
            "target_multiplier": "10-50x (high risk/reward)"
        },
        
        "trading_platforms": [
            TradingPlatform.UNISWAP_V4
        ],
        
        "news_sources": [
            NewsSource.USER_SUBMIT,
            NewsSource.BINANCE_ALPHA  # If Binance lists it
        ],
        
        "why_monitor": "High-volatility meme play on Base. Early DEX listing detection can capture massive pumps. DEX-only requires different strategy."
    },
    
    "PAYAI": {
        "name": "PayAI",
        "full_name": "PayAI Protocol",
        "description": "AI-powered payment infrastructure",
        
        "background": {
            "category": "AI + Payments",
            "launch_date": "2024",
            "team": "AI/Crypto veterans",
            "funding": "Undisclosed",
            "key_features": [
                "AI-driven payment routing",
                "Cross-chain settlement",
                "DeFi integration",
                "AI narrative exposure"
            ]
        },
        
        "upside_potential": {
            "market_position": "AI + Payments intersection",
            "narrative": "AI hype + practical utility",
            "catalysts": [
                "AI narrative strength",
                "Partnership announcements",
                "Exchange listings",
                "Product adoption metrics"
            ],
            "risk_factors": [
                "Competitive payment space",
                "AI narrative saturation",
                "Execution challenges"
            ],
            "target_multiplier": "3-6x from listing price"
        },
        
        "trading_platforms": [
            TradingPlatform.HYPERLIQUID,
            TradingPlatform.ASTER
        ],
        
        "news_sources": [
            NewsSource.BINANCE_SPOT,
            NewsSource.BINANCE_FUTURES,
            NewsSource.UPBIT,
            NewsSource.USER_SUBMIT
        ],
        
        "why_monitor": "AI narrative token. Listing events during AI hype cycles can drive significant momentum. Cross-sector appeal."
    }
}


def get_coin_profile(coin_symbol: str) -> Dict:
    """
    获取币种档案
    
    Args:
        coin_symbol: 币种符号（如 "MON"）
    
    Returns:
        币种档案字典，如果不存在则返回默认档案
    """
    coin_upper = coin_symbol.upper()
    
    if coin_upper in COIN_PROFILES:
        return COIN_PROFILES[coin_upper]
    
    # 默认档案（用于新币种）
    return {
        "name": coin_symbol,
        "full_name": f"{coin_symbol} Token",
        "description": "Monitoring for listing announcements",
        "background": {
            "category": "Unknown",
            "key_features": ["To be determined"]
        },
        "upside_potential": {
            "market_position": "To be analyzed",
            "narrative": "Awaiting market data",
            "catalysts": ["Exchange listings"],
            "risk_factors": ["Insufficient data"],
            "target_multiplier": "To be determined"
        },
        "trading_platforms": [
            TradingPlatform.HYPERLIQUID,
            TradingPlatform.ASTER
        ],
        "news_sources": [
            NewsSource.BINANCE_SPOT,
            NewsSource.BINANCE_FUTURES,
            NewsSource.UPBIT,
            NewsSource.USER_SUBMIT
        ],
        "why_monitor": "New listing opportunity. Monitoring for price discovery and momentum."
    }


def get_all_monitored_coins() -> List[str]:
    """获取所有配置的币种列表"""
    from news_trading.config import SUPPORTED_COINS
    return SUPPORTED_COINS


def get_platform_name(platform: TradingPlatform) -> str:
    """获取平台展示名称"""
    return platform.value


def get_news_source_name(source: NewsSource) -> str:
    """获取消息源展示名称"""
    return source.value

