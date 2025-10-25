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
    爬取URL内容
    
    Args:
        url: 目标URL
        
    Returns:
        提取的文本内容，失败返回None
    """
    try:
        logger.info(f"🌐 开始爬取URL: {url}")
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })
            
            if response.status_code != 200:
                logger.error(f"❌ URL返回异常状态码: {response.status_code}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除script和style标签
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # 提取文本
            text = soup.get_text(separator=' ', strip=True)
            
            # 清理多余空白
            lines = [line.strip() for line in text.split('\n')]
            text = ' '.join([line for line in lines if line])
            
            # 限制长度（防止过长）
            if len(text) > 5000:
                text = text[:5000] + "..."
            
            logger.info(f"✅ 成功爬取内容，长度: {len(text)} 字符")
            return text
    
    except httpx.TimeoutException:
        logger.error(f"❌ 爬取URL超时: {url}")
        return None
    except Exception as e:
        logger.error(f"❌ 爬取URL失败: {e}")
        return None

