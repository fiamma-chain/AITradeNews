#!/usr/bin/env python3
"""
测试脚本：模拟币种上线，触发AI交易流程
"""
import asyncio
import sys
from datetime import datetime
from news_trading.config import MessageSource
from news_trading.message_listeners.base_listener import ListingMessage
from news_trading.news_handler import NewsHandler
from config.settings import settings
from utils.redis_manager import RedisManager
from ai_models.grok_trader import GrokTrader
from trading.hyperliquid.client import HyperliquidClient
from trading.auto_trader import AutoTrader
from trading.multi_platform_trader import MultiPlatformTrader

async def test_coin_listing(coin_symbol: str):
    """测试币种上线流程"""
    print(f"\n{'='*80}")
    print(f"🧪 测试币种上线流程: {coin_symbol}")
    print(f"{'='*80}\n")
    
    # 1. 初始化Redis
    print("📊 初始化Redis...")
    redis_manager = RedisManager()
    
    # 2. 初始化AI
    print(f"🤖 初始化Grok AI...")
    grok_ai = GrokTrader(
        api_key=settings.grok_api_key,
        model=settings.grok_model,
        redis_manager=redis_manager,
        response_history=[],
        use_key_id=4
    )
    
    # 3. 初始化Hyperliquid客户端
    print(f"🔗 初始化Hyperliquid客户端...")
    hl_client = HyperliquidClient(
        private_key=settings.individual_grok_private_key,
        testnet=settings.hyperliquid_testnet
    )
    
    # 4. 初始化自动交易器
    print(f"💼 初始化自动交易器...")
    auto_trader = AutoTrader(
        client=hl_client,
        ai_model=grok_ai,
        redis_manager=redis_manager,
        initial_balance=settings.individual_ai_initial_balance,
        min_confidence=settings.min_confidence,
        min_margin=settings.ai_min_margin,
        max_margin=settings.ai_max_margin,
        max_leverage=settings.ai_max_leverage
    )
    
    # 5. 初始化MultiPlatformTrader
    print(f"🌐 初始化多平台交易器...")
    multi_trader = MultiPlatformTrader(
        trader_name="Grok-Solo",
        redis_manager=redis_manager
    )
    multi_trader.add_platform("Grok-Solo-Hyperliquid", auto_trader)
    
    # 6. 创建消息
    print(f"\n📨 创建上线消息: {coin_symbol}")
    message = ListingMessage(
        source=MessageSource.BINANCE_SPOT,
        coin_symbol=coin_symbol,
        title=f"Binance Will List {coin_symbol} (Test)",
        content=f"This is a test message for {coin_symbol} listing",
        url=f"https://www.binance.com/en/trade/{coin_symbol}_USDT",
        timestamp=datetime.now()
    )
    
    # 7. 创建NewsHandler
    print(f"📡 初始化NewsHandler...")
    news_handler = NewsHandler(redis_manager=redis_manager)
    
    # 手动设置individual_traders（因为我们是独立运行测试）
    news_handler.individual_traders = {
        "Grok": {
            "ai": grok_ai,
            "trader": multi_trader,
            "analyzer": None  # 稍后创建
        }
    }
    
    # 8. 创建NewsAnalyzer
    print(f"🧠 创建NewsAnalyzer...")
    from news_trading.news_analyzer import NewsAnalyzer
    analyzer = NewsAnalyzer(
        ai_model=grok_ai,
        ai_name="Grok"
    )
    news_handler.individual_traders["Grok"]["analyzer"] = analyzer
    
    # 9. 处理消息
    print(f"\n🚀 开始处理上线消息...")
    print(f"   来源: {message.source.value}")
    print(f"   币种: {message.coin_symbol}")
    print(f"   标题: {message.title}")
    print(f"\n⏱️  计时开始...")
    
    start_time = datetime.now()
    
    try:
        await news_handler.handle_message(message)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"\n✅ 测试完成！")
        print(f"⏱️  总耗时: {elapsed:.2f} 秒")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")

async def main():
    if len(sys.argv) < 2:
        print("❌ 用法: python3 test_coin_trading.py <COIN_SYMBOL>")
        print("   示例: python3 test_coin_trading.py ASTER")
        sys.exit(1)
    
    coin_symbol = sys.argv[1].upper()
    await test_coin_listing(coin_symbol)

if __name__ == "__main__":
    asyncio.run(main())

