"""
Logo配置 - 代币、平台、AI模型、消息来源的Logo URL
Logo Configuration - URLs for tokens, platforms, AI models, and news sources

本地Logo路径: /web/images/
- AI模型: /web/images/{ai_name}.png/jpg
- 平台: /web/images/{platform_name}.png/jpg
- 代币: /web/images/coins/{coin_symbol}.png
- 消息来源: /web/images/news_sources/{source_name}.png
"""

# 代币Logo（本地路径）
# 请将logo文件保存到 web/images/coins/ 目录
COIN_LOGOS = {
    "BTC": "/images/coins/btc.png",
    "ETH": "/images/coins/eth.png",
    "SOL": "/images/coins/sol.png",
    "MON": "/images/coins/mon.png",  # Monad
    "MEGA": "/images/coins/mega.png",  # MegaETH
    "PING": "/images/coins/ping.png",  # PING on Base
    "PAYAI": "/images/coins/payai.png",  # PayAI
}

# 交易平台Logo（使用现有文件）
PLATFORM_LOGOS = {
    "Hyperliquid": "/images/hyperliquid.png",
    "Aster": "/images/aster.jpg",
    "Uniswap V4 (Base)": "/images/uniswap.png",  # 需要添加
    "PancakeSwap (BSC)": "/images/pancakeswap.png",  # 需要添加
}

# AI模型Logo（使用现有文件）
AI_MODEL_LOGOS = {
    "GPT-4o": "/images/gpt4.png",
    "Gemini-2.0-Flash": "/images/gemini.png",
    "Grok-4-Fast": "/images/grok.jpg",
    "DeepSeek": "/images/deepseek.jpg",
    "Claude-3.5": "/images/claude.jpg",
    "Qwen-Max": "/images/qwen.jpg",
}

# 消息来源Logo
# 请将logo文件保存到 web/images/news_sources/ 目录
NEWS_SOURCE_LOGOS = {
    "Binance Spot Listing": "/images/news_sources/binance.png",
    "Binance Futures Listing": "/images/news_sources/binance.png",
    "Binance Alpha Project": "/images/news_sources/binance.png",
    "Upbit Listing": "/images/news_sources/upbit.png",
    "User Submission": "/images/news_sources/user.png",
}


def get_coin_logo(symbol: str) -> str:
    """获取代币Logo URL"""
    return COIN_LOGOS.get(symbol.upper(), "https://via.placeholder.com/64/667eea/ffffff?text=" + symbol[:2])


def get_platform_logo(platform_name: str) -> str:
    """获取平台Logo URL"""
    return PLATFORM_LOGOS.get(platform_name, "https://via.placeholder.com/64/48bb78/ffffff?text=P")


def get_ai_model_logo(model_name: str) -> str:
    """获取AI模型Logo URL"""
    return AI_MODEL_LOGOS.get(model_name, "https://via.placeholder.com/64/764ba2/ffffff?text=AI")


def get_news_source_logo(source_name: str) -> str:
    """获取消息来源Logo URL"""
    return NEWS_SOURCE_LOGOS.get(source_name, "https://via.placeholder.com/64/667eea/ffffff?text=N")

