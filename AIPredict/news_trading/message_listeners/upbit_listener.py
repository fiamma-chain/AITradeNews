"""
Upbit 公告监听器
Upbit Announcement Listener
"""
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Optional
from .base_listener import BaseMessageListener, ListingMessage
from ..config import get_coin_symbol, is_supported_coin, MessageSource

logger = logging.getLogger(__name__)


class UpbitAnnouncementListener(BaseMessageListener):
    """Upbit公告监听器（轮询模式）"""
    
    def __init__(self, callback, poll_interval: int = 60):
        """
        初始化Upbit公告监听器
        
        Args:
            callback: 消息回调函数
            poll_interval: 轮询间隔（秒）
        """
        super().__init__(callback)
        self.poll_interval = poll_interval
        self.api_url = "https://api-manager.upbit.com/api/v1/notices"
        self.seen_notice_ids = set()
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
        logger.info(f"🚀 [upbit] 启动公告轮询（间隔: {self.poll_interval}秒）")
        
        while self.running:
            try:
                await self._poll_announcements()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"❌ [upbit] 轮询异常: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _poll_announcements(self):
        """轮询公告"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.api_url,
                    params={
                        "page": 1,
                        "per_page": 20,
                        "thread_name": "general"  # 一般公告
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ [upbit] API返回异常状态码: {response.status_code}")
                    return
                
                data = response.json()
                notices = data.get("data", {}).get("list", [])
                
                # 首次运行，只记录ID
                if self.last_check_time is None:
                    for notice in notices:
                        self.seen_notice_ids.add(notice.get("id"))
                    self.last_check_time = datetime.now()
                    logger.info(f"📋 [upbit] 初始化完成，已记录 {len(notices)} 条历史公告")
                    return
                
                # 处理新公告
                new_notices = [n for n in notices if n.get("id") not in self.seen_notice_ids]
                
                for notice in new_notices:
                    listing_msg = await self.process_message(notice)
                    
                    if listing_msg:
                        logger.info(f"📬 [upbit] 发现上币消息: {listing_msg.coin_symbol}")
                        
                        self.seen_notice_ids.add(notice.get("id"))
                        
                        if self.callback:
                            await self.callback(listing_msg)
                
                self.last_check_time = datetime.now()
        
        except Exception as e:
            logger.error(f"❌ [upbit] 轮询公告时出错: {e}")
    
    async def process_message(self, notice: dict) -> Optional[ListingMessage]:
        """
        处理公告消息
        
        Args:
            notice: 公告数据
            
        Returns:
            ListingMessage 或 None
        """
        try:
            title = notice.get("title", "")
            notice_id = notice.get("id", "")
            created_at = notice.get("created_at")
            
            # 关键词匹配：韩文和英文
            listing_keywords = [
                "신규", "상장", "listing", "launch", "added",
                "지원", "마켓 추가"
            ]
            
            if not any(kw in title.lower() for kw in listing_keywords):
                return None
            
            # 提取币种符号
            coin_symbol = get_coin_symbol(title)
            
            if not coin_symbol:
                logger.debug(f"⚠️ [upbit] 无法识别币种: {title}")
                return None
            
            if not is_supported_coin(coin_symbol):
                logger.debug(f"⚠️ [upbit] 币种不在支持列表: {coin_symbol}")
                return None
            
            # 构建消息
            timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now()
            url = f"https://upbit.com/service_center/notice?id={notice_id}"
            
            return ListingMessage(
                source=MessageSource.UPBIT.value,
                coin_symbol=coin_symbol,
                raw_message=title,
                timestamp=timestamp,
                url=url,
                reliability_score=0.85  # Upbit是韩国主要交易所，可靠性较高
            )
        
        except Exception as e:
            logger.error(f"❌ [upbit] 处理公告时出错: {e}")
            return None


def create_upbit_listener(callback):
    """创建Upbit上币监听器"""
    return UpbitAnnouncementListener(
        callback=callback,
        poll_interval=60
    )

