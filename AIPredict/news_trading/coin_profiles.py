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
    RAYDIUM = "Raydium (Solana)"


class NewsSource(Enum):
    """消息来源"""
    BINANCE_SPOT = "Binance Spot Listing"
    BINANCE_FUTURES = "Binance Futures Listing"
    BINANCE_ALPHA = "Binance Alpha Project"
    UPBIT = "Upbit Listing"
    COINBASE = "Coinbase Listing"
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


# 币种配置档案（清空默认币种，从零开始）
COIN_PROFILES: Dict[str, Dict] = {
    # 用户提交的币种会自动添加到这里
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
        "twitter": "",
        "background": {
            "total_funding": "Unknown",
            "track": "To be determined",
        },
        "project_type": ProjectType.NORMAL,
        "current_stage": ProjectStage.ON_CHAIN,
        "next_stage": ProjectStage.CEX_ALPHA,
        "stage_progress": {
            "completed": [],
            "current": "Awaiting data",
            "upcoming": "To be determined"
        },
        "stage_links": {},
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
