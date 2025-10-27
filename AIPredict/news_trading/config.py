"""
消息驱动交易配置
News-Based Trading Configuration
"""
from typing import Dict, List
from enum import Enum


class TradingMode(Enum):
    """交易模式"""
    MANUAL = "manual"  # 手动模式：用户设置规则
    AI = "ai"          # AI模式：AI自主决策


class MessageSource(Enum):
    """消息来源"""
    BINANCE_SPOT = "binance_spot"
    BINANCE_FUTURES = "binance_futures"
    BINANCE_ALPHA = "binance_alpha"
    UPBIT = "upbit"


# ===== 币种映射配置 =====
# 格式：消息中的币种名 -> 交易对
# CEX币种 -> CEX交易对（Hyperliquid/Aster）
# DEX币种 -> DEX代币符号（Uniswap/PancakeSwap）
COIN_MAPPING = {
    # CEX - 老币
    "BTC": "BTC",
    "BITCOIN": "BTC",
    "ETH": "ETH",
    "ETHEREUM": "ETH",
    "SOL": "SOL",
    "SOLANA": "SOL",
    
    # CEX - 新币
    "MONAD": "MON",
    "MON": "MON",
    "MEGAETH": "MEGA",
    "MEGA": "MEGA",
    
    # DEX - Base链代币
    "PING": "PING",  # Base链Uniswap V4
    
    # 可继续添加...
}

# 支持交易的币种列表（用于过滤）
SUPPORTED_COINS = list(set(COIN_MAPPING.values()))


# ===== 手动模式配置 =====
class ManualModeConfig:
    """手动模式默认配置"""
    
    # 触发规则
    TRIGGER_ON_LISTING = True          # 上币消息触发
    
    # 交易参数
    DEFAULT_LEVERAGE = 20              # 默认杠杆倍数
    DEFAULT_MARGIN = 100.0             # 默认保证金（USDT）
    
    # 止盈止损
    STOP_LOSS_PCT = 0.10              # 止损 10%
    TAKE_PROFIT_PCT = 0.25            # 止盈 25%
    
    # 持仓时间
    MAX_HOLDING_TIME = 3600           # 最大持仓时间（秒），1小时后强制平仓


# ===== AI模式配置 =====
class AIModeConfig:
    """AI模式配置"""
    
    # AI可用的杠杆范围
    MIN_LEVERAGE = 10
    MAX_LEVERAGE = 40
    
    # AI可用的保证金范围
    MIN_MARGIN = 50.0
    MAX_MARGIN = 500.0
    
    # 消息可靠性权重
    SOURCE_RELIABILITY = {
        MessageSource.BINANCE_SPOT: 1.0,      # 最高
        MessageSource.BINANCE_FUTURES: 0.95,  # 次高
        MessageSource.BINANCE_ALPHA: 0.7,     # 中等（孵化项目风险高）
        MessageSource.UPBIT: 0.85,            # 较高（韩国市场影响大）
    }


# ===== WebSocket配置 =====
class WebSocketConfig:
    """WebSocket连接配置"""
    
    # Binance WebSocket
    BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
    BINANCE_ANNOUNCEMENT_API = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
    
    # Upbit WebSocket
    UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"
    UPBIT_ANNOUNCEMENT_API = "https://api.upbit.com/v1/notices"
    
    # 重连配置
    RECONNECT_DELAY = 5               # 重连延迟（秒）
    MAX_RECONNECT_ATTEMPTS = 10       # 最大重连次数


# ===== 系统配置 =====
class SystemConfig:
    """系统级配置"""
    
    # 消息队列
    MESSAGE_QUEUE_SIZE = 100          # 消息队列大小
    MESSAGE_DEDUP_WINDOW = 300        # 消息去重窗口（秒）
    
    # 交易限制
    MAX_CONCURRENT_POSITIONS = 5      # 最大同时持仓数
    COOLDOWN_BETWEEN_TRADES = 60      # 同币种交易冷却时间（秒）
    
    # 日志
    LOG_LEVEL = "INFO"


def get_coin_symbol(message_text: str) -> str:
    """
    从消息中提取币种符号
    
    Args:
        message_text: 消息文本（如 "Binance will list MONAD"）
        
    Returns:
        Hyperliquid交易对符号，如 "MON"，未找到返回None
    """
    message_upper = message_text.upper()
    
    # 遍历映射表查找匹配
    for key, value in COIN_MAPPING.items():
        if key in message_upper:
            return value
    
    return None


def is_supported_coin(symbol: str) -> bool:
    """检查币种是否支持交易"""
    return symbol in SUPPORTED_COINS


def add_coin_mapping(message_name: str, hl_symbol: str):
    """动态添加币种映射"""
    COIN_MAPPING[message_name.upper()] = hl_symbol.upper()
    if hl_symbol.upper() not in SUPPORTED_COINS:
        SUPPORTED_COINS.append(hl_symbol.upper())


def remove_coin_mapping(message_name: str):
    """移除币种映射"""
    if message_name.upper() in COIN_MAPPING:
        del COIN_MAPPING[message_name.upper()]

