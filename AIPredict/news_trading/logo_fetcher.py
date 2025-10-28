"""
从Twitter/X获取项目Logo
"""
import httpx
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


async def fetch_twitter_avatar(twitter_url: str, symbol: str) -> str:
    """
    从Twitter URL获取用户头像并保存到本地
    
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
        
        # 方案1: 直接访问Twitter，获取头像（通过HTML解析）
        avatar_url = None
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                # 尝试访问Twitter页面
                response = await client.get(f"https://x.com/{username}")
                
                if response.status_code == 200:
                    # 从HTML中提取头像URL
                    # Twitter头像通常在og:image或profile_image_url中
                    og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
                    
                    if og_image_match:
                        avatar_url = og_image_match.group(1)
                        logger.info(f"✅ 从Twitter获取到头像URL: {avatar_url}")
                    else:
                        # 尝试其他模式
                        profile_img_match = re.search(r'"profile_image_url_https":"([^"]+)"', response.text)
                        if profile_img_match:
                            avatar_url = profile_img_match.group(1).replace(r'\/', '/')
                            logger.info(f"✅ 从Twitter JSON获取到头像URL: {avatar_url}")
        
        except Exception as e:
            logger.warning(f"⚠️ 直接访问Twitter失败: {e}")
        
        # 方案2: 使用syndication API（公开端点）
        if not avatar_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Twitter的公开syndication API
                    api_url = f"https://cdn.syndication.twimg.com/widgets/followbutton/info.json?screen_names={username}"
                    response = await client.get(api_url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data and len(data) > 0:
                            avatar_url = data[0].get('profile_image_url_https', '')
                            # 替换为更高清版本
                            if avatar_url:
                                avatar_url = avatar_url.replace('_normal', '_400x400')
                                logger.info(f"✅ 从syndication API获取到头像URL: {avatar_url}")
            except Exception as e:
                logger.warning(f"⚠️ syndication API获取失败: {e}")
        
        if not avatar_url:
            logger.warning(f"❌ 无法获取头像")
            return None
        
        # 下载头像
        async with httpx.AsyncClient(timeout=15.0) as client:
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

