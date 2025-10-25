"""
URL内容爬取工具
URL Content Scraper for User-Submitted News
"""
import logging
import httpx
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


async def scrape_url_content(url: str) -> Optional[str]:
    """
    爬取URL内容，如果爬取失败则从URL推断信息
    
    Args:
        url: 目标URL
        
    Returns:
        提取的文本内容，失败返回None
    """
    try:
        logger.info(f"🌐 开始爬取URL: {url}")
        
        # 增强的headers，模拟真实浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            # 接受200和202状态码
            if response.status_code not in [200, 202]:
                logger.warning(f"⚠️  URL返回状态码 {response.status_code}，尝试从URL推断")
                return _infer_from_url(url)
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否是WAF挑战页面
            if len(response.text) < 5000 and ('gokuProps' in response.text or 'challenge' in response.text.lower()):
                logger.warning("⚠️  检测到WAF保护，尝试从URL推断")
                return _infer_from_url(url)
            
            # 优先提取标题
            title = None
            
            # 尝试多种标题提取方法
            title_selectors = [
                # Meta标签（最可靠）
                ('meta', {'property': 'og:title'}),
                ('meta', {'name': 'twitter:title'}),
                ('meta', {'name': 'title'}),
                # HTML标签
                ('h1', {}),
                ('title', {}),
            ]
            
            for tag_name, attrs in title_selectors:
                if tag_name == 'meta':
                    tag = soup.find(tag_name, attrs)
                    if tag and tag.get('content'):
                        title = tag.get('content').strip()
                        if title:
                            break
                else:
                    tag = soup.find(tag_name, attrs)
                    if tag:
                        title = tag.get_text(strip=True)
                        if title and len(title) > 10:  # 确保标题有意义
                            break
            
            # 如果找到标题
            if title:
                logger.info(f"✅ 成功提取标题: {title}")
                
                # 尝试提取描述
                description = None
                desc_selectors = [
                    ('meta', {'name': 'description'}),
                    ('meta', {'property': 'og:description'}),
                    ('meta', {'name': 'twitter:description'}),
                ]
                
                for tag_name, attrs in desc_selectors:
                    tag = soup.find(tag_name, attrs)
                    if tag and tag.get('content'):
                        description = tag.get('content').strip()[:500]
                        if description:
                            break
                
                # 组合标题和描述
                if description:
                    content = f"{title}. {description}"
                else:
                    content = title
                
                logger.info(f"✅ 内容长度: {len(content)} 字符")
                return content
            
            # 如果没有找到标题，尝试从URL推断
            logger.warning("⚠️  未找到标题，尝试从URL推断")
            return _infer_from_url(url)
    
    except httpx.TimeoutException:
        logger.error(f"❌ 爬取URL超时，尝试从URL推断")
        return _infer_from_url(url)
    except Exception as e:
        logger.error(f"❌ 爬取URL失败: {e}，尝试从URL推断")
        return _infer_from_url(url)


def _infer_from_url(url: str) -> Optional[str]:
    """
    从URL推断内容（当爬取失败时的回退方案）
    
    Args:
        url: URL字符串
        
    Returns:
        推断的内容描述
    """
    try:
        logger.info(f"🔍 从URL推断内容: {url}")
        
        url_lower = url.lower()
        
        # 识别交易所
        exchange = None
        if 'binance' in url_lower:
            exchange = 'Binance'
        elif 'coinbase' in url_lower:
            exchange = 'Coinbase'
        elif 'upbit' in url_lower:
            exchange = 'Upbit'
        elif 'bybit' in url_lower:
            exchange = 'Bybit'
        elif 'okx' in url_lower or 'okex' in url_lower:
            exchange = 'OKX'
        elif 'kraken' in url_lower:
            exchange = 'Kraken'
        elif 'kucoin' in url_lower:
            exchange = 'KuCoin'
        
        # 识别事件类型（按优先级）
        event_type = None
        
        # 优先检查组合关键词
        if 'will-list' in url_lower or 'will_list' in url_lower or 'willlist' in url_lower:
            event_type = 'will list'
        elif 'new-listing' in url_lower or 'new_listing' in url_lower:
            event_type = 'new listing'
        elif 'list' in url_lower or 'listing' in url_lower:
            event_type = 'listing'
        elif 'launch' in url_lower:
            event_type = 'launch'
        elif 'delist' in url_lower:
            event_type = 'delisting'
        
        # 识别市场类型
        market_type = None
        if 'futures' in url_lower or 'perpetual' in url_lower:
            market_type = 'futures'
        elif 'spot' in url_lower:
            market_type = 'spot'
        
        # 构造描述
        parts = []
        if exchange:
            parts.append(exchange)
        
        # 组合市场类型和事件类型
        if market_type and event_type:
            parts.append(f'{market_type} {event_type}')
        elif event_type:
            parts.append(event_type)
        elif market_type:
            parts.append(f'{market_type} announcement')
        else:
            # 如果在announcement路径下，推测是公告
            if 'announcement' in url_lower or 'support' in url_lower:
                # 尝试从URL推测是listing相关
                if exchange and ('detail' in url_lower or 'article' in url_lower):
                    parts.append('listing announcement')
                else:
                    parts.append('announcement')
            else:
                parts.append('announcement')
        
        description = ' '.join(parts) if parts else 'Cryptocurrency announcement'
        
        logger.info(f"✅ 推断内容: {description}")
        return description
    
    except Exception as e:
        logger.error(f"❌ URL推断失败: {e}")
        return "Cryptocurrency listing announcement"

