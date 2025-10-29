"""
币安公告监听器
Binance Announcement Listener
"""
import asyncio
import logging
import httpx
import re
from datetime import datetime
from typing import Optional
from .base_listener import BaseMessageListener, ListingMessage
from ..config import get_coin_symbol, is_supported_coin, MessageSource

logger = logging.getLogger(__name__)


class BinanceAnnouncementListener(BaseMessageListener):
    """币安公告监听器（轮询模式）"""
    
    def __init__(self, callback, catalog_id: int, source: MessageSource, poll_interval: int = 30):
        """
        初始化币安公告监听器
        
        Args:
            callback: 消息回调函数
            catalog_id: 公告类型ID
                - 48: 币安现货新币上线
                - 49: 币安合约新币上线  
                - 157: 币安孵化项目
            source: 消息来源枚举
            poll_interval: 轮询间隔（秒）
        """
        super().__init__(callback)
        self.catalog_id = catalog_id
        self.source = source
        self.poll_interval = poll_interval
        self.api_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
        self.seen_article_ids = set()  # 已处理的公告ID
        self.last_check_time = None
        
        logger.info(f"🔧 [{self.source.value}] 监听器初始化")
        logger.info(f"   URL: {self.api_url}")
        logger.info(f"   catalogId: {self.catalog_id}")
    
    async def connect(self):
        """（此监听器不需要WebSocket连接）"""
        pass
    
    async def subscribe(self):
        """（此监听器不需要订阅）"""
        pass
    
    async def start(self):
        """启动轮询"""
        self.running = True
        logger.info(f"🚀 [{self.source.value}] 启动公告轮询（间隔: {self.poll_interval}秒）")
        
        while self.running:
            try:
                await self._poll_announcements()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"❌ [{self.source.value}] 轮询异常: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _poll_announcements(self):
        """轮询公告"""
        try:
            # 使用代理访问 Binance API（如果配置了代理）
            import os
            proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
            
            client_kwargs = {"timeout": 10.0}
            if proxy:
                client_kwargs["proxy"] = proxy
                logger.debug(f"使用代理: {proxy}")
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                # 添加真实的请求头，避免被反爬虫拦截
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://www.binance.com",
                    "Referer": "https://www.binance.com/"
                }
                
                response = await client.post(
                    self.api_url,
                    json={
                        "type": 1,
                        "catalogId": self.catalog_id,
                        "pageNo": 1,
                        "pageSize": 10
                    },
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ [{self.source.value}] API调用失败")
                    logger.warning(f"   URL: {self.api_url}")
                    logger.warning(f"   catalogId: {self.catalog_id}")
                    logger.warning(f"   状态码: {response.status_code}")
                    logger.warning(f"   响应: {response.text[:200]}")
                    return
                
                data = response.json()
                articles = data.get("data", {}).get("catalogs", [{}])[0].get("articles", [])
                
                # 首次运行，只记录ID，不处理历史消息
                if self.last_check_time is None:
                    for article in articles:
                        self.seen_article_ids.add(article.get("code"))
                    self.last_check_time = datetime.now()
                    logger.info(f"📋 [{self.source.value}] 初始化完成，已记录 {len(articles)} 条历史公告")
                    return
                
                # 处理新公告
                new_articles = [a for a in articles if a.get("code") not in self.seen_article_ids]
                
                for article in new_articles:
                    listing_msg = await self.process_message(article)
                    
                    if listing_msg:
                        logger.info(f"📬 [{self.source.value}] 发现上币消息: {listing_msg.coin_symbol}")
                        
                        # 标记为已处理
                        self.seen_article_ids.add(article.get("code"))
                        
                        # 调用回调
                        if self.callback:
                            await self.callback(listing_msg)
                
                self.last_check_time = datetime.now()
        
        except Exception as e:
            logger.error(f"❌ [{self.source.value}] 轮询公告时出错: {e}")
    
    async def process_message(self, article: dict) -> Optional[ListingMessage]:
        """
        处理公告消息
        
        Args:
            article: 公告数据
            
        Returns:
            ListingMessage 或 None
        """
        try:
            title = article.get("title", "")
            code = article.get("code", "")
            release_date = article.get("releaseDate")
            
            # 关键词匹配：判断是否为上币公告
            listing_keywords = [
                "will list", "lists", "listing", "新币上线", "上线",
                "opens trading", "adds", "launches"
            ]
            
            if not any(kw.lower() in title.lower() for kw in listing_keywords):
                return None
            
            # 提取币种符号
            coin_symbol = get_coin_symbol(title)
            
            if not coin_symbol:
                logger.debug(f"⚠️ [{self.source.value}] 无法识别币种: {title}")
                return None
            
            if not is_supported_coin(coin_symbol):
                logger.debug(f"⚠️ [{self.source.value}] 币种不在支持列表: {coin_symbol}")
                return None
            
            # 构建消息
            timestamp = datetime.fromtimestamp(release_date / 1000) if release_date else datetime.now()
            url = f"https://www.binance.com/en/support/announcement/{code}"
            
            return ListingMessage(
                source=self.source.value,
                coin_symbol=coin_symbol,
                raw_message=title,
                timestamp=timestamp,
                url=url,
                reliability_score=self._calculate_reliability(title)
            )
        
        except Exception as e:
            logger.error(f"❌ [{self.source.value}] 处理公告时出错: {e}")
            return None
    
    def _calculate_reliability(self, title: str) -> float:
        """
        基于标题内容计算可靠性评分
        
        Args:
            title: 公告标题
            
        Returns:
            可靠性评分 (0-1)
        """
        score = 1.0
        
        # 包含"perpetual"或"futures"则为合约上线，评分更高
        if any(kw in title.lower() for kw in ["perpetual", "futures", "usdt-m"]):
            score = 1.0
        # 现货上线
        elif "spot" in title.lower():
            score = 0.95
        # 孵化项目风险较高
        elif "alpha" in title.lower() or "innovation" in title.lower():
            score = 0.7
        
        return score


# 便捷的工厂函数
def create_binance_spot_listener(callback):
    """创建币安现货上币监听器"""
    return BinanceAnnouncementListener(
        callback=callback,
        catalog_id=48,
        source=MessageSource.BINANCE_SPOT,
        poll_interval=30
    )


def create_binance_futures_listener(callback):
    """创建币安合约上币监听器"""
    return BinanceAnnouncementListener(
        callback=callback,
        catalog_id=49,
        source=MessageSource.BINANCE_FUTURES,
        poll_interval=30
    )


def create_binance_alpha_listener(callback):
    """创建币安Alpha孵化项目监听器"""
    return BinanceAnnouncementListener(
        callback=callback,
        catalog_id=157,
        source=MessageSource.BINANCE_ALPHA,
        poll_interval=60  # Alpha项目更新频率较低，可延长轮询间隔
    )

