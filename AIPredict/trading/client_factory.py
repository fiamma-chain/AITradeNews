"""
交易客户端工厂 - 自动路由到CEX或DEX
Trading Client Factory - Automatic routing to CEX or DEX
"""
import logging
from typing import Optional
from config.settings import settings
from trading.base_client import BaseExchangeClient
from trading.hyperliquid.client import HyperliquidClient
from trading.aster.client import AsterClient

# DEX imports
from trading.dex import (
    is_dex_token,
    get_token_chain,
    UniswapV4Client,
    PancakeSwapClient,
    RaydiumClient,
)

logger = logging.getLogger(__name__)


class ClientFactory:
    """客户端工厂 - 根据代币自动选择交易平台"""
    
    @staticmethod
    def create_client(coin: str, private_key: str = None, platform: str = None) -> Optional[BaseExchangeClient]:
        """
        创建交易客户端
        
        Args:
            coin: 代币符号
            private_key: 私钥
            platform: 指定平台（可选），如果不指定则自动选择
        
        Returns:
            交易客户端实例
        """
        coin_upper = coin.upper()
        
        # 1. 如果指定了平台，直接创建对应客户端
        if platform:
            return ClientFactory._create_platform_client(platform, private_key)
        
        # 2. 检查是否为DEX代币
        if is_dex_token(coin_upper):
            logger.info(f"🔍 [{coin_upper}] 检测到DEX代币，路由到DEX平台")
            return ClientFactory._create_dex_client(coin_upper, private_key)
        
        # 3. 默认使用CEX（Hyperliquid或Aster）
        logger.info(f"🔍 [{coin_upper}] CEX代币，使用默认平台")
        return ClientFactory._create_cex_client(private_key)
    
    @staticmethod
    def _create_dex_client(coin: str, private_key: str) -> Optional[BaseExchangeClient]:
        """
        创建DEX客户端
        
        Args:
            coin: 代币符号
            private_key: 私钥
        
        Returns:
            DEX客户端实例
        """
        try:
            chain = get_token_chain(coin)
            
            if chain == "base":
                # Base链 - Uniswap V4
                if not settings.base_chain_enabled:
                    logger.error(f"❌ Base链未启用，无法交易 {coin}")
                    return None
                
                if not settings.base_private_key:
                    logger.error(f"❌ Base链私钥未配置")
                    return None
                
                logger.info(f"✅ 创建Uniswap V4客户端 (Base链)")
                return UniswapV4Client(
                    private_key=settings.base_private_key,
                    rpc_url=settings.base_rpc_url
                )
            
            elif chain == "bsc":
                # BSC链 - PancakeSwap
                if not settings.bsc_chain_enabled:
                    logger.error(f"❌ BSC链未启用，无法交易 {coin}")
                    return None
                
                if not settings.bsc_private_key:
                    logger.error(f"❌ BSC链私钥未配置")
                    return None
                
                logger.info(f"✅ 创建PancakeSwap客户端 (BSC链)")
                return PancakeSwapClient(
                    private_key=settings.bsc_private_key,
                    rpc_url=settings.bsc_rpc_url
                )
            
            elif chain == "solana":
                # Solana链 - Raydium
                if not settings.solana_chain_enabled:
                    logger.error(f"❌ Solana链未启用，无法交易 {coin}")
                    return None
                
                if not settings.solana_private_key:
                    logger.error(f"❌ Solana链私钥未配置")
                    return None
                
                logger.info(f"✅ 创建Raydium客户端 (Solana链)")
                return RaydiumClient(
                    private_key=settings.solana_private_key,
                    rpc_url=settings.solana_rpc_url
                )
            
            else:
                logger.error(f"❌ 不支持的链: {chain}")
                return None
        
        except Exception as e:
            logger.error(f"❌ 创建DEX客户端失败: {e}")
            return None
    
    @staticmethod
    def _create_cex_client(private_key: str) -> Optional[BaseExchangeClient]:
        """
        创建CEX客户端（默认使用第一个启用的平台）
        
        Args:
            private_key: 私钥
        
        Returns:
            CEX客户端实例
        """
        try:
            # 检查启用的平台
            if settings.enable_hyperliquid:
                logger.info(f"✅ 创建Hyperliquid客户端")
                return HyperliquidClient(private_key, settings.hyperliquid_testnet)
            
            # 默认使用Aster
            logger.info(f"✅ 创建Aster客户端")
            return AsterClient(private_key, settings.aster_testnet)
        
        except Exception as e:
            logger.error(f"❌ 创建CEX客户端失败: {e}")
            return None
    
    @staticmethod
    def _create_platform_client(platform: str, private_key: str) -> Optional[BaseExchangeClient]:
        """
        根据平台名称创建客户端
        
        Args:
            platform: 平台名称 (hyperliquid, aster, uniswap, pancakeswap)
            private_key: 私钥
        
        Returns:
            客户端实例
        """
        platform_lower = platform.lower()
        
        if platform_lower == "hyperliquid":
            return HyperliquidClient(private_key, settings.hyperliquid_testnet)
        
        elif platform_lower == "aster":
            return AsterClient(private_key, settings.aster_testnet)
        
        elif platform_lower in ["uniswap", "uniswap_v4", "base"]:
            if not settings.base_chain_enabled or not settings.base_private_key:
                logger.error(f"❌ Base链未配置")
                return None
            return UniswapV4Client(
                private_key=settings.base_private_key,
                rpc_url=settings.base_rpc_url
            )
        
        elif platform_lower in ["pancakeswap", "bsc"]:
            if not settings.bsc_chain_enabled or not settings.bsc_private_key:
                logger.error(f"❌ BSC链未配置")
                return None
            return PancakeSwapClient(
                private_key=settings.bsc_private_key,
                rpc_url=settings.bsc_rpc_url
            )
        
        elif platform_lower in ["raydium", "solana"]:
            if not settings.solana_chain_enabled or not settings.solana_private_key:
                logger.error(f"❌ Solana链未配置")
                return None
            return RaydiumClient(
                private_key=settings.solana_private_key,
                rpc_url=settings.solana_rpc_url
            )
        
        else:
            logger.error(f"❌ 不支持的平台: {platform}")
            return None
    
    @staticmethod
    def get_supported_platforms(coin: str) -> list:
        """
        获取代币支持的平台列表
        
        Args:
            coin: 代币符号
        
        Returns:
            支持的平台列表
        """
        coin_upper = coin.upper()
        
        if is_dex_token(coin_upper):
            chain = get_token_chain(coin_upper)
            if chain == "base":
                return ["uniswap_v4"] if settings.base_chain_enabled else []
            elif chain == "bsc":
                return ["pancakeswap"] if settings.bsc_chain_enabled else []
            elif chain == "solana":
                return ["raydium"] if settings.solana_chain_enabled else []
            else:
                return []
        else:
            # CEX代币
            platforms = []
            if settings.enable_hyperliquid:
                platforms.append("hyperliquid")
            platforms.append("aster")  # Aster默认启用
            return platforms


# 全局工厂实例
client_factory = ClientFactory()

