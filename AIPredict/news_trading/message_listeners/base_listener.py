"""
消息监听器基类
Base Message Listener
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ListingMessage:
    """上币消息数据类"""
    source: str                    # 消息来源 (binance_spot, upbit, etc.)
    coin_symbol: str               # 币种符号 (BTC, MON, etc.)
    raw_message: str               # 原始消息内容
    timestamp: datetime            # 消息时间
    url: Optional[str] = None      # 消息链接
    reliability_score: float = 1.0 # 可靠性评分 (0-1)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "source": self.source,
            "coin_symbol": self.coin_symbol,
            "raw_message": self.raw_message,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "reliability_score": self.reliability_score
        }


class BaseMessageListener(ABC):
    """消息监听器基类"""
    
    def __init__(self, callback: Callable[[ListingMessage], None]):
        """
        初始化监听器
        
        Args:
            callback: 收到新消息时的回调函数
        """
        self.callback = callback
        self.running = False
        self.ws = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5
    
    @abstractmethod
    async def connect(self):
        """连接到WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe(self):
        """订阅消息"""
        pass
    
    @abstractmethod
    async def process_message(self, message: dict) -> Optional[ListingMessage]:
        """
        处理接收到的消息
        
        Args:
            message: 原始消息字典
            
        Returns:
            解析后的ListingMessage，如果不是上币消息则返回None
        """
        pass
    
    async def start(self):
        """启动监听器"""
        self.running = True
        logger.info(f"🚀 [{self.__class__.__name__}] 启动消息监听器")
        
        while self.running:
            try:
                await self.connect()
                await self.subscribe()
                await self._listen_loop()
            except Exception as e:
                logger.error(f"❌ [{self.__class__.__name__}] 监听器异常: {e}", exc_info=True)
                
                if self.running:
                    self._reconnect_attempts += 1
                    
                    if self._reconnect_attempts >= self._max_reconnect_attempts:
                        logger.error(f"❌ [{self.__class__.__name__}] 达到最大重连次数，停止监听")
                        break
                    
                    logger.info(f"🔄 [{self.__class__.__name__}] {self._reconnect_delay}秒后重连 (尝试 {self._reconnect_attempts}/{self._max_reconnect_attempts})")
                    await asyncio.sleep(self._reconnect_delay)
    
    async def _listen_loop(self):
        """监听循环"""
        if not self.ws:
            return
        
        logger.info(f"✅ [{self.__class__.__name__}] 开始监听消息...")
        
        try:
            async for raw_message in self.ws:
                if not self.running:
                    break
                
                try:
                    # 处理消息
                    listing_msg = await self.process_message(raw_message)
                    
                    if listing_msg:
                        logger.info(f"📬 [{self.__class__.__name__}] 收到上币消息: {listing_msg.coin_symbol}")
                        
                        # 重置重连计数
                        self._reconnect_attempts = 0
                        
                        # 调用回调函数
                        if self.callback:
                            await self.callback(listing_msg)
                
                except Exception as e:
                    logger.error(f"⚠️ [{self.__class__.__name__}] 处理消息时出错: {e}")
        
        finally:
            await self.close()
    
    async def stop(self):
        """停止监听器"""
        logger.info(f"🛑 [{self.__class__.__name__}] 停止消息监听器")
        self.running = False
        await self.close()
    
    async def close(self):
        """关闭WebSocket连接"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"⚠️ [{self.__class__.__name__}] 关闭连接时出错: {e}")
            finally:
                self.ws = None

