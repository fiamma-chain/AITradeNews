"""
交易币种过滤器
用于限制只交易指定的加密货币
"""
from typing import List, Optional
from config.settings import settings, get_allowed_symbols, is_symbol_allowed
import logging

logger = logging.getLogger(__name__)


class SymbolFilter:
    """币种过滤器"""
    
    def __init__(self):
        self.allowed_symbols = get_allowed_symbols()
        self._log_configuration()
    
    def _log_configuration(self):
        """记录配置信息"""
        if not self.allowed_symbols:
            logger.info("🌐 交易币种: 全部允许")
        else:
            logger.info(f"🎯 交易币种限制: {', '.join(self.allowed_symbols)}")
    
    def is_allowed(self, symbol: str) -> bool:
        """
        检查币种是否允许交易
        
        Args:
            symbol: 币种符号（如 BTC, ETH）
            
        Returns:
            是否允许交易
        """
        return is_symbol_allowed(symbol)
    
    def filter_symbols(self, symbols: List[str]) -> List[str]:
        """
        过滤币种列表，只保留允许交易的
        
        Args:
            symbols: 币种列表
            
        Returns:
            过滤后的币种列表
        """
        if not self.allowed_symbols:
            return symbols  # 全部允许
        
        filtered = [s for s in symbols if self.is_allowed(s)]
        
        if len(filtered) < len(symbols):
            removed = set(symbols) - set(filtered)
            logger.debug(f"过滤掉不允许的币种: {', '.join(removed)}")
        
        return filtered
    
    def get_default_symbol(self) -> str:
        """
        获取默认交易币种
        
        Returns:
            默认币种（如果有限制则返回第一个允许的币种，否则返回 BTC）
        """
        if self.allowed_symbols:
            return self.allowed_symbols[0]
        return "BTC"
    
    def get_allowed_list(self) -> List[str]:
        """获取允许交易的币种列表"""
        return self.allowed_symbols.copy() if self.allowed_symbols else []
    
    def validate_symbol(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        验证币种并返回错误信息
        
        Args:
            symbol: 币种符号
            
        Returns:
            (是否有效, 错误信息)
        """
        symbol_upper = symbol.upper()
        
        if not self.is_allowed(symbol_upper):
            if self.allowed_symbols:
                allowed_str = ', '.join(self.allowed_symbols)
                return False, f"币种 {symbol_upper} 不在允许列表中。允许的币种: {allowed_str}"
            else:
                return False, f"币种 {symbol_upper} 无效"
        
        return True, None


# 全局实例
symbol_filter = SymbolFilter()


def check_symbol_before_trade(symbol: str) -> bool:
    """
    交易前检查币种是否允许（装饰器辅助函数）
    
    Args:
        symbol: 币种符号
        
    Returns:
        是否允许交易
    """
    is_valid, error_msg = symbol_filter.validate_symbol(symbol)
    
    if not is_valid:
        logger.warning(f"⚠️  交易被阻止: {error_msg}")
        return False
    
    return True

