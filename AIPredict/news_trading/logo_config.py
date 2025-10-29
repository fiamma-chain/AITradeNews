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
# ✅ 已添加的logo文件
COIN_LOGOS = {
    "BTC": "/images/coins/btc.png",      # 需要添加
    "ETH": "/images/coins/eth.png",      # 需要添加
    "SOL": "/images/coins/sol.png",      # 需要添加
    "MON": "/images/coins/monad.jpg",    # ✅ 已添加
    "MEGA": "/images/coins/mega.jpg",    # ✅ 已添加
    "PING": "/images/coins/ping.jpg",    # ✅ 已添加
    "PAYAI": "/images/coins/payai.jpg",  # ✅ 已添加
}

# 交易平台Logo（使用现有文件）
PLATFORM_LOGOS = {
    "Hyperliquid": "/images/hyperliquid.png",  # ✅ 已存在
    "Aster": None,  # 移除Aster logo
    "Uniswap V4 (Base)": "/images/uniswap.png",      # 需要添加
    "PancakeSwap (BSC)": "/images/pancakeswap.png",  # 需要添加
    "Raydium (Solana)": "/images/raydium.jpg",       # ✅ 已添加
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
# ✅ 已添加的logo文件
NEWS_SOURCE_LOGOS = {
    "Binance Spot Listing": "/images/news_sources/binance.jpg",    # ✅ 已添加
    "Binance Futures Listing": "/images/news_sources/binance.jpg",  # ✅ 已添加
    "Binance Alpha Project": "/images/news_sources/binance.jpg",    # ✅ 已添加
    "Upbit Listing": "/images/news_sources/upbit.jpg",              # ✅ 已添加
    "User Submission": "/images/news_sources/user.png",             # 需要添加
}


def get_coin_logo(symbol: str) -> str:
    """获取代币Logo URL"""
    symbol_upper = symbol.upper()
    if symbol_upper in COIN_LOGOS:
        return COIN_LOGOS[symbol_upper]
    # 返回SVG占位符而不是placeholder.com（被墙）
    text = symbol_upper[:2]
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Crect width='64' height='64' fill='%23667eea'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='24' fill='white'%3E{text}%3C/text%3E%3C/svg%3E"


def get_platform_logo(platform_name: str) -> str:
    """获取平台Logo URL"""
    if platform_name in PLATFORM_LOGOS:
        return PLATFORM_LOGOS[platform_name]
    # 返回SVG占位符
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Crect width='64' height='64' fill='%2348bb78'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='24' fill='white'%3EP%3C/text%3E%3C/svg%3E"


def get_ai_model_logo(model_name: str) -> str:
    """获取AI模型Logo URL"""
    if model_name in AI_MODEL_LOGOS:
        return AI_MODEL_LOGOS[model_name]
    # 返回SVG占位符
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Crect width='64' height='64' fill='%23764ba2'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='20' fill='white'%3EAI%3C/text%3E%3C/svg%3E"


def get_news_source_logo(source_name: str) -> str:
    """获取消息来源Logo URL"""
    if source_name in NEWS_SOURCE_LOGOS:
        return NEWS_SOURCE_LOGOS[source_name]
    # 返回SVG占位符
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Crect width='64' height='64' fill='%23667eea'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-size='24' fill='white'%3EN%3C/text%3E%3C/svg%3E"

