"""
配置管理模块
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 交易平台配置
    enabled_platforms: str = "hyperliquid,aster"  # 启用的平台，逗号分隔
    
    # Hyperliquid 配置（默认主网）
    hyperliquid_testnet: bool = False
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    
    # Aster 配置（仅支持主网）
    aster_testnet: bool = False
    aster_api_url: str = "https://fapi.asterdex.com"
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 46000
    
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    balance_history_ttl: int = 86400 * 7  # 7天过期
    
    # 允许交易的币种
    allowed_trading_symbols: str = "BTC"
    
    # AI API Keys
    claude_api_key: str = ""
    openai_api_key: str = ""
    gpt_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"  # 快速模型，适合交易决策
    qwen_api_key: str = ""
    qwen_model: str = "qwen-turbo"  # qwen-turbo, qwen-max, qwen-plus
    qwen_use_international: bool = False  # True: 国际版, False: 国内版
    grok_api_key: str = ""
    grok_model: str = "grok-4-fast-non-reasoning"  # 快速版本（比标准版快9倍）
    deepseek_api_key: str = ""
    
    # AI 交易配置
    ai_initial_balance: float = 240.0  # 组账户初始余额（Alpha组和Beta组）
    individual_ai_initial_balance: float = 200.0  # 独立AI交易者初始余额
    ai_min_margin: float = 120.0  # 最小保证金（U）
    ai_max_margin: float = 240.0  # 最大保证金（U）
    ai_max_leverage: float = 5.0  # 最大杠杆倍数（AI可根据信心度动态调整1-5x）
    ai_stop_loss_pct: float = 0.15  # 止损比例 15%
    ai_take_profit_pct: float = 0.30  # 止盈比例 30%
    
    # 分组共识配置（默认主网）
    group_1_name: str = "Alpha组"
    group_1_ais: str = ""
    group_1_private_key: str = ""
    group_2_name: str = "Beta组"
    group_2_ais: str = ""
    group_2_private_key: str = ""
    consensus_min_votes: int = 2
    consensus_interval: int = 300
    min_confidence: float = 60.0
    
    # 多平台对比模式
    multi_platform_mode: bool = True  # 是否启用多平台对比模式
    platform_comparison_enabled: bool = True  # 是否显示平台对比
    
    # 独立AI交易者私钥配置（可选，用于AI竞技场模式）
    # 如果配置了私钥，则该AI会作为独立交易者启动
    # 留空则不启用该AI作为独立交易者
    individual_deepseek_private_key: str = ""
    individual_claude_private_key: str = ""
    individual_grok_private_key: str = ""
    individual_gpt_private_key: str = ""
    individual_gemini_private_key: str = ""
    individual_qwen_private_key: str = ""
    
    # 消息驱动交易系统配置
    news_trading_enabled: bool = False  # 是否启用消息驱动交易
    news_trading_ais: str = "claude,gpt,deepseek"  # AI模式使用的AI列表，逗号分隔
    
    # 功能开关（性能测试）
    enable_consensus_trading: bool = True   # 是否启用共识交易（Alpha/Beta组）
    enable_individual_trading: bool = True  # 是否启用独立AI常规交易
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_allowed_symbols():
    """获取允许交易的币种列表"""
    if not settings.allowed_trading_symbols:
        return []  # 空列表表示全部允许
    
    symbols = [s.strip().upper() for s in settings.allowed_trading_symbols.split(',')]
    return [s for s in symbols if s]  # 过滤空字符串


def is_symbol_allowed(symbol: str) -> bool:
    """检查币种是否允许交易"""
    allowed = get_allowed_symbols()
    if not allowed:  # 空列表表示全部允许
        return True
    return symbol.upper() in allowed


def get_enabled_platforms():
    """获取启用的交易平台列表"""
    if not settings.enabled_platforms:
        return ["hyperliquid"]  # 默认只启用 Hyperliquid
    
    platforms = [p.strip().lower() for p in settings.enabled_platforms.split(',')]
    return [p for p in platforms if p]  # 过滤空字符串


def is_platform_enabled(platform: str) -> bool:
    """检查平台是否启用"""
    enabled = get_enabled_platforms()
    return platform.lower() in enabled


def get_individual_traders_config():
    """
    获取独立AI交易者配置
    
    Returns:
        List[Dict]: [{"ai_name": "DeepSeek", "private_key": "0x123"}, ...]
    
    Raises:
        ValueError: 如果配置了私钥但私钥格式无效
    """
    traders = []
    
    # AI模型配置映射
    ai_configs = [
        ("DeepSeek", settings.individual_deepseek_private_key),
        ("Claude", settings.individual_claude_private_key),
        ("Grok", settings.individual_grok_private_key),
        ("GPT", settings.individual_gpt_private_key),
        ("Gemini", settings.individual_gemini_private_key),
        ("Qwen", settings.individual_qwen_private_key),
    ]
    
    for ai_name, private_key in ai_configs:
        if private_key and private_key.strip():
            private_key = private_key.strip()
            
            # 验证私钥格式
            if not private_key.startswith('0x'):
                raise ValueError(
                    f"❌ {ai_name} 独立交易者私钥格式错误: 必须以 '0x' 开头\n"
                    f"   配置项: INDIVIDUAL_{ai_name.upper()}_PRIVATE_KEY"
                )
            
            if len(private_key) != 66:  # 0x + 64位十六进制
                raise ValueError(
                    f"❌ {ai_name} 独立交易者私钥格式错误: 长度必须是66个字符 (0x + 64位十六进制)\n"
                    f"   配置项: INDIVIDUAL_{ai_name.upper()}_PRIVATE_KEY\n"
                    f"   当前长度: {len(private_key)}"
                )
            
            traders.append({
                "ai_name": ai_name,
                "private_key": private_key
            })
    
    return traders


def get_news_trading_ais():
    """获取消息驱动交易使用的AI列表"""
    if not settings.news_trading_ais:
        return []
    
    ais = [ai.strip().lower() for ai in settings.news_trading_ais.split(',')]
    return [ai for ai in ais if ai]



