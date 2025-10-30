"""
交易精度配置模块

统一管理不同交易所、不同币种的精度要求
"""
from decimal import Decimal
from typing import Dict, Tuple


class PrecisionConfig:
    """精度配置管理器"""
    
    # Aster 精度配置
    ASTER_PRECISION = {
        "BTC": {
            "quantity_precision": 3,  # 数量精度：3位小数
            "price_precision": 1,     # 价格精度：1位小数
            "quantity_step": "0.001", # 数量步长
            "price_tick": "0.1",      # 价格步长
            "min_quantity": "0.001",  # 最小数量
            "min_notional": "50"      # 最小名义价值（USDT）- 与AI_MIN_POSITION_SIZE一致
        },
        "ETH": {
            "quantity_precision": 3,
            "price_precision": 2,
            "quantity_step": "0.001",
            "price_tick": "0.01",
            "min_quantity": "0.001",
            "min_notional": "50"      # 最小名义价值（USDT）- 与AI_MIN_POSITION_SIZE一致
        }
    }
    
    # Hyperliquid 精度配置
    HYPERLIQUID_PRECISION = {
        "BTC": {
            "quantity_precision": 5,  # 数量精度：5位小数
            "price_precision": 0,     # 价格精度：整数
            "quantity_step": "0.00001",
            "price_tick": "1",
            "min_quantity": "0.00001",
            "min_notional": "50"      # 最小名义价值（USD）- 与AI_MIN_POSITION_SIZE一致
        },
        "ETH": {
            "quantity_precision": 4,
            "price_precision": 0,
            "quantity_step": "0.0001",
            "price_tick": "1",
            "min_quantity": "0.0001",
            "min_notional": "50"      # 最小名义价值（USD）- 与AI_MIN_POSITION_SIZE一致
        }
    }
    
    @classmethod
    def get_aster_precision(cls, coin: str) -> Dict:
        """
        获取Aster平台的精度配置
        
        Args:
            coin: 币种符号（如 BTC, ETH）
            
        Returns:
            精度配置字典
        """
        return cls.ASTER_PRECISION.get(coin, cls.ASTER_PRECISION["BTC"])
    
    @classmethod
    def get_hyperliquid_precision(cls, coin: str) -> Dict:
        """
        获取Hyperliquid平台的精度配置（动态查询）
        
        Args:
            coin: 币种符号（如 BTC, ETH）
            
        Returns:
            精度配置字典
        """
        # 先检查缓存
        if coin in cls.HYPERLIQUID_PRECISION:
            return cls.HYPERLIQUID_PRECISION[coin]
        
        # 动态从 Hyperliquid 查询精度
        try:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants
            
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            meta = info.meta_and_asset_ctxs()
            
            for asset in meta[0]['universe']:
                if asset['name'] == coin:
                    sz_decimals = asset.get('szDecimals', 5)
                    
                    # 根据 szDecimals 计算 quantity_step
                    if sz_decimals == 0:
                        quantity_step = "1"  # 整数
                        min_quantity = "1"
                    else:
                        quantity_step = f"0.{'0' * (sz_decimals - 1)}1"
                        min_quantity = quantity_step
                    
                    precision_config = {
                        "quantity_precision": sz_decimals,
                        "price_precision": 0,
                        "quantity_step": quantity_step,
                        "price_tick": "1",
                        "min_quantity": min_quantity,
                        "min_notional": "10"
                    }
                    
                    # 缓存配置
                    cls.HYPERLIQUID_PRECISION[coin] = precision_config
                    return precision_config
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️  无法获取 {coin} 的精度配置，使用BTC默认值: {e}")
        
        # 失败时返回 BTC 配置
        return cls.HYPERLIQUID_PRECISION["BTC"]
    
    @classmethod
    def format_aster_quantity(cls, coin: str, quantity: float, round_down: bool = True) -> Tuple[float, str]:
        """
        格式化Aster数量
        
        Args:
            coin: 币种
            quantity: 原始数量
            round_down: 是否向下取整（开仓用），否则四舍五入（平仓用）
            
        Returns:
            (格式化后的数量, 数量字符串)
        """
        from decimal import ROUND_DOWN, ROUND_HALF_UP
        
        config = cls.get_aster_precision(coin)
        step = Decimal(config["quantity_step"])
        
        decimal_qty = Decimal(str(quantity))
        
        if round_down:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_DOWN))
        else:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_HALF_UP))
        
        # 确保不小于最小数量
        min_qty = float(config["min_quantity"])
        if formatted < min_qty and formatted > 0:
            formatted = min_qty
        
        return formatted, str(formatted)
    
    @classmethod
    def format_aster_price(cls, coin: str, price: float) -> Tuple[float, str]:
        """
        格式化Aster价格
        
        Args:
            coin: 币种
            price: 原始价格
            
        Returns:
            (格式化后的价格, 价格字符串)
        """
        from decimal import ROUND_HALF_UP
        
        config = cls.get_aster_precision(coin)
        tick = Decimal(config["price_tick"])
        
        decimal_price = Decimal(str(price))
        formatted = float(decimal_price.quantize(tick, rounding=ROUND_HALF_UP))
        
        return formatted, str(formatted)
    
    @classmethod
    def format_hyperliquid_quantity(cls, coin: str, quantity: float, round_down: bool = True) -> Tuple[float, str]:
        """
        格式化Hyperliquid数量
        
        Args:
            coin: 币种
            quantity: 原始数量
            round_down: 是否向下取整（开仓用），否则四舍五入（平仓用）
            
        Returns:
            (格式化后的数量, 数量字符串)
        """
        from decimal import ROUND_DOWN, ROUND_HALF_UP
        
        config = cls.get_hyperliquid_precision(coin)
        step = Decimal(config["quantity_step"])
        
        decimal_qty = Decimal(str(quantity))
        
        if round_down:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_DOWN))
        else:
            formatted = float(decimal_qty.quantize(step, rounding=ROUND_HALF_UP))
        
        # 确保不小于最小数量
        min_qty = float(config["min_quantity"])
        if formatted < min_qty and formatted > 0:
            formatted = min_qty
        
        return formatted, str(formatted)
    
    @classmethod
    def format_hyperliquid_price(cls, coin: str, price: float) -> Tuple[float, str]:
        """
        格式化Hyperliquid价格
        
        Args:
            coin: 币种
            price: 原始价格
            
        Returns:
            (格式化后的价格, 价格字符串)
        """
        from decimal import ROUND_HALF_UP
        
        config = cls.get_hyperliquid_precision(coin)
        tick = Decimal(config["price_tick"])
        
        decimal_price = Decimal(str(price))
        formatted = float(decimal_price.quantize(tick, rounding=ROUND_HALF_UP))
        
        return formatted, str(formatted)
    
    @classmethod
    def validate_aster_order(cls, coin: str, quantity: float, price: float = None) -> Tuple[bool, str]:
        """
        验证Aster订单参数
        
        Returns:
            (是否有效, 错误信息)
        """
        config = cls.get_aster_precision(coin)
        
        # 检查最小数量
        min_qty = float(config["min_quantity"])
        if quantity < min_qty:
            return False, f"数量 {quantity} 小于最小值 {min_qty}"
        
        # 检查最小名义价值
        if price:
            notional = quantity * price
            min_notional = float(config["min_notional"])
            if notional < min_notional:
                return False, f"名义价值 {notional:.2f} USDT 小于最小值 {min_notional} USDT"
        
        return True, ""
    
    @classmethod
    def validate_hyperliquid_order(cls, coin: str, quantity: float, price: float = None) -> Tuple[bool, str]:
        """
        验证Hyperliquid订单参数
        
        Returns:
            (是否有效, 错误信息)
        """
        config = cls.get_hyperliquid_precision(coin)
        
        # 检查最小数量
        min_qty = float(config["min_quantity"])
        if quantity < min_qty:
            return False, f"数量 {quantity} 小于最小值 {min_qty}"
        
        # 检查最小名义价值
        if price:
            notional = quantity * price
            min_notional = float(config["min_notional"])
            if notional < min_notional:
                return False, f"名义价值 {notional:.2f} USD 小于最小值 {min_notional} USD"
        
        return True, ""


# 全局实例
precision_config = PrecisionConfig()

