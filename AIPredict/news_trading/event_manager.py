"""
新闻交易事件管理器
用于推送实时活动到前端
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)


class EventManager:
    """事件管理器 - SSE推送"""
    
    def __init__(self, max_history: int = 50):
        """
        初始化事件管理器
        
        Args:
            max_history: 保留的历史事件数量
        """
        self.subscribers = []  # 订阅者列表
        self.event_history = deque(maxlen=max_history)  # 事件历史
        
    def add_subscriber(self, queue: asyncio.Queue):
        """添加订阅者"""
        self.subscribers.append(queue)
        logger.info(f"📡 新订阅者加入，当前订阅数: {len(self.subscribers)}")
        
    def remove_subscriber(self, queue: asyncio.Queue):
        """移除订阅者"""
        if queue in self.subscribers:
            self.subscribers.remove(queue)
            logger.info(f"📡 订阅者离开，当前订阅数: {len(self.subscribers)}")
    
    async def push_event(self, event_type: str, data: Dict[str, Any]):
        """
        推送事件到所有订阅者
        
        Args:
            event_type: 事件类型 (monitor_started, ai_analysis, trade_opened, etc.)
            data: 事件数据
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # 添加到历史
        self.event_history.append(event)
        
        # 推送给所有订阅者
        dead_subscribers = []
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.warning(f"⚠️  推送事件失败: {e}")
                dead_subscribers.append(queue)
        
        # 清理死连接
        for queue in dead_subscribers:
            self.remove_subscriber(queue)
        
        logger.debug(f"📤 事件已推送: {event_type} -> {len(self.subscribers)} 订阅者")
    
    def get_history(self) -> List[Dict]:
        """获取历史事件"""
        return list(self.event_history)


# 全局事件管理器实例
event_manager = EventManager()

