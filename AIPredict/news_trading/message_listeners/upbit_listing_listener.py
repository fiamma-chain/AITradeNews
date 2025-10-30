"""
Upbit 交易对监听器（官方 API）
Upbit Trading Pair Listener
"""
import asyncio
import logging
import httpx
import os
from datetime import datetime
from typing import Set
from .base_listener import BaseMessageListener, ListingMessage
from ..config import get_coin_symbol, is_supported_coin, MessageSource

logger = logging.getLogger(__name__)


class UpbitListingListener(BaseMessageListener):
    """Upbit 交易对监听器（轮询模式，使用官方 market API）"""
    
    def __init__(self, callback, poll_interval: int = 30):
        """
        初始化 Upbit 交易对监听器
        
        Args:
            callback: 消息回调函数
            poll_interval: 轮询间隔（秒）
        """
        super().__init__(callback)
        self.poll_interval = poll_interval
        self.api_url = "https://api.upbit.com/v1/market/all"
        self.seen_symbols: Set[str] = set()  # 已知的交易对
        self.first_run = True
        
        logger.info(f"🔧 [upbit] 监听器初始化")
        logger.info(f"   URL: {self.api_url}")
    
    async def connect(self):
        """（此监听器不需要WebSocket连接）"""
        pass
    
    async def subscribe(self):
        """（此监听器不需要订阅）"""
        pass
    
    async def process_message(self, message):
        """处理上币消息"""
        if self.callback:
            await self.callback(message)
    
    async def start(self):
        """启动轮询"""
        self.running = True
        logger.info(f"🚀 [upbit] 启动交易对监听（间隔: {self.poll_interval}秒）")
        
        while self.running:
            try:
                await self._poll_trading_pairs()
            except Exception as e:
                logger.error(f"❌ [upbit] 轮询失败: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _poll_trading_pairs(self):
        """轮询交易对列表"""
        try:
            # 配置代理
            proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
            
            client_kwargs = {"timeout": 10.0}
            if proxy:
                client_kwargs["proxy"] = proxy
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                }
                
                # Upbit API 参数：isDetails=false 只返回交易对列表
                response = await client.get(
                    self.api_url,
                    params={"isDetails": "false"},
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ [upbit] API调用失败")
                    logger.warning(f"   URL: {self.api_url}")
                    logger.warning(f"   状态码: {response.status_code}")
                    logger.warning(f"   响应: {response.text[:200]}")
                    return
                
                markets = response.json()
                
                # 筛选 KRW（韩元）交易对
                krw_pairs = []
                for market in markets:
                    market_code = market.get("market", "")
                    if market_code.startswith("KRW-"):
                        krw_pairs.append(market_code)
                
                logger.info(f"✅ [upbit] 获取到 {len(krw_pairs)} 个 KRW 交易对")
                
                # 检查是否是测试模式
                from config.settings import settings
                test_mode = settings.news_trading_test_mode
                
                # 首次运行处理
                if self.first_run:
                    if test_mode:
                        # 测试模式：不记录任何交易对，下次轮询时会把所有监控币种当作"新上线"
                        self.first_run = False
                        logger.warning(f"🧪 [upbit] 测试模式已启用 - 将把监控币种视为新上线")
                        return
                    else:
                        # 正常模式：记录现有交易对
                        self.seen_symbols = set(krw_pairs)
                        self.first_run = False
                        logger.info(f"📋 [upbit] 初始化完成，已记录 {len(self.seen_symbols)} 个交易对")
                        return
                
                # 检测新交易对
                new_symbols = set(krw_pairs) - self.seen_symbols
                
                if new_symbols:
                    logger.info(f"🆕 [upbit] 检测到 {len(new_symbols)} 个新交易对: {new_symbols}")
                    
                    for market_code in new_symbols:
                        # 提取币种名称（格式：KRW-BTC）
                        coin = market_code.replace("KRW-", "")
                        
                        # 检查是否是监控的币种
                        if is_supported_coin(coin):
                            message = ListingMessage(
                                source=MessageSource.UPBIT.value,
                                coin_symbol=coin,
                                raw_message=f"Upbit Listed {coin}/KRW - New trading pair detected: {market_code}",
                                timestamp=datetime.now(),
                                url=f"https://upbit.com/exchange?code=CRIX.UPBIT.{market_code}"
                            )
                            
                            logger.info(f"🎯 [upbit] 发现监控币种: {coin}")
                            await self.process_message(message)
                    
                    # 更新已知交易对
                    self.seen_symbols.update(new_symbols)
                
        except Exception as e:
            logger.error(f"❌ [upbit] 轮询失败: {e}", exc_info=True)
    
    async def stop(self):
        """停止监听"""
        self.running = False
        logger.info(f"🛑 [upbit] 已停止")


def create_upbit_listener(callback):
    """创建 Upbit 监听器"""
    return UpbitListingListener(
        callback=callback,
        poll_interval=30
    )

