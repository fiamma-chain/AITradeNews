"""
币安交易对监听器（官方 API）
Binance Trading Pair Listener
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


class BinanceListingListener(BaseMessageListener):
    """币安交易对监听器（轮询模式，使用官方 exchangeInfo API）"""
    
    def __init__(self, callback, source: MessageSource, poll_interval: int = 30):
        """
        初始化币安交易对监听器
        
        Args:
            callback: 消息回调函数
            source: 消息来源枚举
            poll_interval: 轮询间隔（秒）
        """
        super().__init__(callback)
        self.source = source
        self.poll_interval = poll_interval
        
        # 根据来源设置不同的 API
        if source == MessageSource.BINANCE_SPOT:
            self.api_url = "https://api.binance.com/api/v3/exchangeInfo"
            self.pair_suffix = "USDT"  # 监听 USDT 交易对
        elif source == MessageSource.BINANCE_FUTURES:
            self.api_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
            self.pair_suffix = "USDT"  # 监听 USDT 永续合约
        else:
            # Alpha 项目暂时保留公告模式
            self.api_url = None
            
        self.seen_symbols: Set[str] = set()  # 已知的交易对
        self.first_run = True
        
        logger.info(f"🔧 [{self.source.value}] 监听器初始化")
        logger.info(f"   URL: {self.api_url}")
        logger.info(f"   监听交易对后缀: {self.pair_suffix}")
    
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
        if not self.api_url:
            logger.warning(f"⚠️ [{self.source.value}] 未配置 API URL，跳过启动")
            return
            
        self.running = True
        logger.info(f"🚀 [{self.source.value}] 启动交易对监听（间隔: {self.poll_interval}秒）")
        
        while self.running:
            try:
                await self._poll_trading_pairs()
            except Exception as e:
                logger.error(f"❌ [{self.source.value}] 轮询失败: {e}")
            
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
                }
                
                response = await client.get(self.api_url, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ [{self.source.value}] API调用失败")
                    logger.warning(f"   URL: {self.api_url}")
                    logger.warning(f"   状态码: {response.status_code}")
                    logger.warning(f"   响应: {response.text[:200]}")
                    return
                
                data = response.json()
                symbols = data.get("symbols", [])
                
                # 筛选 USDT 交易对且处于交易状态
                active_pairs = []
                for symbol_info in symbols:
                    symbol = symbol_info.get("symbol", "")
                    status = symbol_info.get("status", "")
                    
                    # 只关注 USDT 交易对且状态为 TRADING
                    if symbol.endswith(self.pair_suffix) and status == "TRADING":
                        active_pairs.append(symbol)
                
                logger.info(f"✅ [{self.source.value}] 获取到 {len(active_pairs)} 个活跃交易对")
                
                # 检查是否是测试模式
                from config.settings import settings
                test_mode = settings.news_trading_test_mode
                
                # 首次运行处理
                if self.first_run:
                    if test_mode:
                        # 测试模式：不记录任何交易对，下次轮询时会把所有监控币种当作"新上线"
                        self.first_run = False
                        logger.warning(f"🧪 [{self.source.value}] 测试模式已启用 - 将把监控币种视为新上线")
                        return
                    else:
                        # 正常模式：记录现有交易对
                        self.seen_symbols = set(active_pairs)
                        self.first_run = False
                        logger.info(f"📋 [{self.source.value}] 初始化完成，已记录 {len(self.seen_symbols)} 个交易对")
                        return
                
                # 检测新交易对
                new_symbols = set(active_pairs) - self.seen_symbols
                
                if new_symbols:
                    logger.info(f"🆕 [{self.source.value}] 检测到 {len(new_symbols)} 个新交易对: {new_symbols}")
                    
                    for symbol in new_symbols:
                        # 提取币种名称（去掉 USDT 后缀）
                        coin = symbol.replace(self.pair_suffix, "")
                        
                        # 检查是否是监控的币种
                        if is_supported_coin(coin):
                            message = ListingMessage(
                                source=self.source.value,
                                coin_symbol=coin,
                                raw_message=f"Binance Listed {coin}/{self.pair_suffix} - New trading pair detected: {symbol}",
                                timestamp=datetime.now(),
                                url=f"https://www.binance.com/en/trade/{coin}_{self.pair_suffix}"
                            )
                            
                            logger.info(f"🎯 [{self.source.value}] 发现监控币种: {coin}")
                            await self.process_message(message)
                    
                    # 更新已知交易对
                    self.seen_symbols.update(new_symbols)
                
        except Exception as e:
            logger.error(f"❌ [{self.source.value}] 轮询失败: {e}", exc_info=True)
    
    async def stop(self):
        """停止监听"""
        self.running = False
        logger.info(f"🛑 [{self.source.value}] 已停止")


def create_binance_spot_listener(callback):
    """创建币安现货监听器"""
    return BinanceListingListener(
        callback=callback,
        source=MessageSource.BINANCE_SPOT,
        poll_interval=30
    )


def create_binance_futures_listener(callback):
    """创建币安合约监听器"""
    return BinanceListingListener(
        callback=callback,
        source=MessageSource.BINANCE_FUTURES,
        poll_interval=30
    )

