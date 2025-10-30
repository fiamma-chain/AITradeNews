"""
从Twitter/X获取项目Logo
使用第三方服务（unavatar.io）和备用方案
"""
import httpx
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


async def fetch_twitter_avatar(twitter_url: str, symbol: str) -> str:
    """
    从Twitter URL获取用户头像并保存到本地（优化版：快速失败）
    
    Args:
        twitter_url: Twitter/X的URL (https://twitter.com/xxx 或 https://x.com/xxx)
        symbol: 币种符号，用于保存文件名
    
    Returns:
        保存的logo相对路径，如 /images/MON.jpg
    """
    try:
        # 提取用户名
        username_match = re.search(r'(?:twitter\.com|x\.com)/([^/?]+)', twitter_url)
        if not username_match:
            logger.warning(f"❌ 无法从URL提取Twitter用户名: {twitter_url}")
            return None
        
        username = username_match.group(1)
        logger.info(f"🔍 提取Twitter用户名: {username}")
        
        avatar_url = None
        
        # 🚀 方案1: 使用unavatar.io服务（最快）
        # 注：Twitter API 无法直接获取图片，仅返回URL，且需要复杂的OAuth认证
        try:
            unavatar_url = f"https://unavatar.io/x/{username}?fallback=false"
            
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(unavatar_url)
                
                if response.status_code == 200 and response.headers.get('content-type', '').startswith('image/'):
                    avatar_url = unavatar_url
                    logger.info(f"✅ 从unavatar.io获取到头像URL: {avatar_url}")
                else:
                    logger.warning(f"⚠️ unavatar.io返回异常: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ unavatar.io获取失败: {e}")
        
        # 🚀 方案2: 备用头像服务（快速生成）
        if not avatar_url:
            try:
                backup_url = f"https://ui-avatars.com/api/?name={username}&size=200&background=667eea&color=fff&bold=true"
                
                async with httpx.AsyncClient(timeout=3.0) as client:  # 更短超时
                    response = await client.get(backup_url)
                    if response.status_code == 200:
                        avatar_url = backup_url
                        logger.info(f"✅ 从备用服务获取到头像URL: {backup_url}")
            except Exception as e:
                logger.warning(f"⚠️ 备用服务获取失败: {e}")
        
        if not avatar_url:
            logger.warning(f"❌ 无法获取头像")
            return None
        
        # 下载头像
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:  # 减少超时
            img_response = await client.get(avatar_url)
            
            if img_response.status_code != 200:
                logger.warning(f"❌ 下载头像失败: HTTP {img_response.status_code}")
                return None
            
            # 确定文件扩展名
            content_type = img_response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                ext = 'jpg'  # 默认
            
            # 保存到本地
            save_dir = Path(__file__).parent.parent / "web" / "images"
            save_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{symbol.upper()}.{ext}"
            save_path = save_dir / filename
            
            with open(save_path, 'wb') as f:
                f.write(img_response.content)
            
            logger.info(f"✅ Logo已保存: {save_path}")
            
            # 返回相对路径
            return f"/images/{filename}"
    
    except Exception as e:
        logger.error(f"❌ 获取Twitter头像失败: {e}", exc_info=True)
        return None


async def fetch_favicon_from_url(url: str, symbol: str) -> str:
    """
    从URL获取网站favicon作为备选方案
    
    Args:
        url: 网站URL
        symbol: 币种符号
    
    Returns:
        保存的logo相对路径
    """
    try:
        # 提取域名
        domain_match = re.search(r'https?://([^/]+)', url)
        if not domain_match:
            return None
        
        domain = domain_match.group(1)
        
        # 常见favicon位置
        favicon_urls = [
            f"https://{domain}/favicon.ico",
            f"https://{domain}/favicon.png",
            f"https://{domain}/apple-touch-icon.png",
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for favicon_url in favicon_urls:
                try:
                    response = await client.get(favicon_url)
                    if response.status_code == 200:
                        # 保存
                        save_dir = Path(__file__).parent.parent / "web" / "images"
                        save_dir.mkdir(parents=True, exist_ok=True)
                        
                        ext = 'png' if 'png' in favicon_url else 'ico'
                        filename = f"{symbol.upper()}.{ext}"
                        save_path = save_dir / filename
                        
                        with open(save_path, 'wb') as f:
                            f.write(response.content)
                        
                        logger.info(f"✅ Favicon已保存: {save_path}")
                        return f"/images/{filename}"
                
                except Exception as e:
                    continue
        
        return None
    
    except Exception as e:
        logger.error(f"❌ 获取favicon失败: {e}")
        return None


def get_default_logo(symbol: str) -> str:
    """
    生成默认Logo占位符（使用SVG）
    
    Args:
        symbol: 币种符号
    
    Returns:
        SVG data URL
    """
    # 生成带币种符号的SVG
    first_chars = symbol[:2] if len(symbol) >= 2 else symbol
    
    return (
        f"data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 "
        f"width=%2264%22 height=%2264%22%3E%3Crect width=%2264%22 height=%2264%22 "
        f"fill=%22%23667eea%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 "
        f"dominant-baseline=%22middle%22 text-anchor=%22middle%22 "
        f"font-size=%2224%22 fill=%22white%22%3E{first_chars}%3C/text%3E%3C/svg%3E"
    )

