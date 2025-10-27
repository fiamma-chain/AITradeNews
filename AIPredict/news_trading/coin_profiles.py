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


class ProjectType(Enum):
    """项目类型"""
    MEGA = "Mega Project"      # 特大级项目
    NORMAL = "Normal Project"  # 普通项目
    MEME = "Meme Token"       # Meme币


class ProjectStage(Enum):
    """项目阶段"""
    # 特大级项目阶段
    PRE_MARKET = "Pre-market Contract"  # 盘前合约
    CEX_SPOT = "CEX Spot Listing"       # 交易所现货
    
    # 普通/Meme项目阶段
    ON_CHAIN = "On-chain Trading"       # 链上交易
    CEX_ALPHA = "CEX Alpha + Futures"   # 交易所Alpha+合约
    CEX_LISTING = "CEX Spot Listing"    # 交易所现货


# 币种配置档案
COIN_PROFILES: Dict[str, Dict] = {
    "MON": {
        "name": "Monad",
        "full_name": "Monad Blockchain",
        "description": "High-performance Layer-1 blockchain with parallel execution",
        
        # 项目背景
        "background": {
            "total_funding": "$225M",           # 总投资额
            "track": "Layer-1 Blockchain",      # 赛道定位
            "lead_investors": "Paradigm, Electric Capital, Coinbase Ventures",
            "team": "Former Jump Trading engineers"
        },
        
        # 项目类型和阶段
        "project_type": ProjectType.MEGA,
        "current_stage": ProjectStage.PRE_MARKET,
        "next_stage": ProjectStage.CEX_SPOT,
        "stage_progress": {
            "completed": [],
            "current": "Pre-market Contract",
            "upcoming": "CEX Spot Listing (Expected Q2 2025)"
        },
        
        "upside_potential": {
            "market_position": "Next-gen Layer-1 competitor to Solana/Ethereum",
            "narrative": "High-performance blockchain narrative",
            "catalysts": [
                "Mainnet launch expected Q2 2025",
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
        "name": "MEGA",
        "full_name": "MegaETH",
        "description": "Real-time Ethereum with sub-millisecond latency",
        
        # 项目背景
        "background": {
            "total_funding": "$20M",              # 总投资额
            "track": "Layer-2 Scaling",           # 赛道定位
            "lead_investors": "Dragonfly Capital, Vitalik Buterin",
            "team": "Research-driven blockchain team"
        },
        
        # 项目类型和阶段
        "project_type": ProjectType.MEGA,
        "current_stage": ProjectStage.PRE_MARKET,
        "next_stage": ProjectStage.CEX_SPOT,
        "stage_progress": {
            "completed": [],
            "current": "Pre-market Contract",
            "upcoming": "CEX Spot Listing (Expected 2025)"
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
        
        # 项目背景
        "background": {
            "total_funding": "Fair Launch (No VC)",   # 总投资额
            "track": "Meme Token",                    # 赛道定位
            "lead_investors": "Community-driven",
            "team": "Anonymous / Community"
        },
        
        # 项目类型和阶段
        "project_type": ProjectType.MEME,
        "current_stage": ProjectStage.ON_CHAIN,
        "next_stage": ProjectStage.CEX_ALPHA,
        "stage_progress": {
            "completed": [],
            "current": "On-chain Trading (Uniswap V4)",
            "upcoming": "CEX Alpha + Futures (If momentum builds)"
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
        
        # 项目背景
        "background": {
            "total_funding": "$8M",                   # 总投资额
            "track": "AI + Payments",                 # 赛道定位
            "lead_investors": "Binance Labs, OKX Ventures",
            "team": "AI/Crypto veterans"
        },
        
        # 项目类型和阶段
        "project_type": ProjectType.NORMAL,
        "current_stage": ProjectStage.ON_CHAIN,
        "next_stage": ProjectStage.CEX_ALPHA,
        "stage_progress": {
            "completed": [],
            "current": "On-chain Trading (DEX)",
            "upcoming": "CEX Alpha + Futures (Expected Q1 2025)"
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
            TradingPlatform.PANCAKESWAP,
            TradingPlatform.HYPERLIQUID,
            TradingPlatform.ASTER
        ],
        
        "news_sources": [
            NewsSource.BINANCE_SPOT,
            NewsSource.BINANCE_FUTURES,
            NewsSource.BINANCE_ALPHA,
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
            "total_funding": "Unknown",
            "track": "To be determined",
            "lead_investors": "N/A",
            "team": "N/A"
        },
        "project_type": ProjectType.NORMAL,
        "current_stage": ProjectStage.ON_CHAIN,
        "next_stage": ProjectStage.CEX_ALPHA,
        "stage_progress": {
            "completed": [],
            "current": "Awaiting data",
            "upcoming": "To be determined"
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
