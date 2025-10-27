"""
Coinbase公告监听器
Coinbase Announcement Listener
"""
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Optional
from .base_listener import BaseMessageListener, ListingMessage
from ..config import get_coin_symbol, is_supported_coin, MessageSource

logger = logging.getLogger(__name__)


class CoinbaseAnnouncementListener(BaseMessageListener):
    """Coinbase公告监听器（轮询模式）"""
    
    def __init__(self, callback, poll_interval: int = 60):
        """
        初始化Coinbase公告监听器
        
        Args:
            callback: 消息回调函数
            poll_interval: 轮询间隔（秒），Coinbase较少发布，可以设置更长间隔
        """
        super().__init__(callback)
        self.poll_interval = poll_interval
        self.api_url = "https://api.coinbase.com/api/v3/brokerage/market/products"
        self.blog_url = "https://blog.coinbase.com"
        self.seen_products = set()  # 已处理的产品
        self.last_check_time = None
    
    async def connect(self):
        """（此监听器不需要WebSocket连接）"""
        pass
    
    async def subscribe(self):
        """（此监听器不需要订阅）"""
        pass
    
    async def start(self):
        """启动轮询"""
        self.running = True
        logger.info(f"🚀 [Coinbase] 启动Coinbase上币监听器，轮询间隔: {self.poll_interval}秒")
        
        # 首次轮询立即执行
        await self._poll_listings()
        
        # 定时轮询
        while self.running:
            await asyncio.sleep(self.poll_interval)
            if self.running:
                await self._poll_listings()
    
    async def _poll_listings(self):
        """轮询Coinbase新上币信息"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 方法1: 查询交易对列表（新币种会出现在这里）
                response = await client.get(self.api_url)
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ [Coinbase] API返回状态码: {response.status_code}")
                    return
                
                data = response.json()
                products = data.get("products", [])
                
                # 检查新币种
                for product in products:
                    product_id = product.get("product_id", "")
                    base_currency = product.get("base_currency_id", "")
                    quote_currency = product.get("quote_currency_id", "")
                    status = product.get("status", "")
                    
                    # 只关注USD交易对且状态为online
                    if quote_currency != "USD" or status != "online":
                        continue
                    
                    # 检查是否为新币种
                    if product_id not in self.seen_products:
                        self.seen_products.add(product_id)
                        
                        # 首次启动时，不触发通知（避免大量旧数据）
                        if self.last_check_time is None:
                            continue
                        
                        # 处理新上币
                        listing_msg = await self.process_message(product)
                        if listing_msg and self.callback:
                            await self.callback(listing_msg)
                
                self.last_check_time = datetime.now()
                logger.debug(f"✅ [Coinbase] 完成一轮轮询，当前监控 {len(self.seen_products)} 个交易对")
        
        except httpx.TimeoutException:
            logger.warning(f"⚠️ [Coinbase] 请求超时")
        except Exception as e:
            logger.error(f"❌ [Coinbase] 轮询时出错: {e}")
    
    async def process_message(self, product: dict) -> Optional[ListingMessage]:
        """
        处理产品数据
        
        Args:
            product: 产品数据
            
        Returns:
            ListingMessage 或 None
        """
        try:
            product_id = product.get("product_id", "")
            base_currency = product.get("base_currency_id", "")
            display_name = product.get("display_name", "")
            
            # 使用base_currency作为币种符号
            coin_symbol = get_coin_symbol(base_currency)
            
            if not coin_symbol:
                coin_symbol = base_currency.upper()
            
            if not is_supported_coin(coin_symbol):
                logger.debug(f"⚠️ [Coinbase] 币种不在支持列表: {coin_symbol}")
                return None
            
            # 构建消息
            title = f"Coinbase Lists {display_name} ({base_currency}-USD)"
            url = f"https://www.coinbase.com/price/{base_currency.lower()}"
            
            return ListingMessage(
                source=MessageSource.COINBASE.value,
                coin_symbol=coin_symbol,
                raw_message=title,
                timestamp=datetime.now(),
                url=url,
                reliability_score=0.95  # Coinbase是美国主要交易所，可靠性很高
            )
        
        except Exception as e:
            logger.error(f"❌ [Coinbase] 处理产品数据时出错: {e}")
            return None


def create_coinbase_listener(callback):
    """创建Coinbase上币监听器"""
    return CoinbaseAnnouncementListener(
        callback=callback,
        poll_interval=60  # Coinbase较少发布新币，60秒轮询一次
    )

