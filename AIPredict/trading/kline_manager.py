"""
K线数据管理器
用于收集和维护日内时间序列数据
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from collections import deque

logger = logging.getLogger(__name__)


class KlineManager:
    """K线数据管理器"""
    
    def __init__(self, max_klines: int = 16):
        """
        初始化K线管理器
        
        Args:
            max_klines: 保留的最大K线数量（默认16根，即4小时的15分钟K线）
        """
        self.max_klines = max_klines
        self.klines: deque = deque(maxlen=max_klines)
        self.current_kline: Dict = None
        self.last_update_time: datetime = None
        
    def update_price(self, price: float, volume: float = 0):
        """
        更新价格数据
        
        Args:
            price: 当前价格
            volume: 成交量
        """
        now = datetime.now()
        
        # 获取当前15分钟的时间戳（向下取整到15分钟）
        current_period = now.replace(second=0, microsecond=0)
        minute = current_period.minute
        period_minute = (minute // 15) * 15
        current_period = current_period.replace(minute=period_minute)
        
        # 如果是新的15分钟周期，保存旧K线，开始新K线
        if self.current_kline is None or self.current_kline['time'] != current_period:
            if self.current_kline is not None:
                # 保存完成的K线
                self.klines.append(self.current_kline.copy())
                logger.info(f"📊 K线完成: {self.current_kline['time'].strftime('%H:%M')} "
                           f"O:{self.current_kline['open']:.0f} H:{self.current_kline['high']:.0f} "
                           f"L:{self.current_kline['low']:.0f} C:{self.current_kline['close']:.0f}")
            
            # 开始新K线
            self.current_kline = {
                'time': current_period,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
        else:
            # 更新当前K线
            self.current_kline['high'] = max(self.current_kline['high'], price)
            self.current_kline['low'] = min(self.current_kline['low'], price)
            self.current_kline['close'] = price
            self.current_kline['volume'] += volume
        
        self.last_update_time = now
    
    def get_klines(self, count: int = None) -> List[Dict]:
        """
        获取K线列表
        
        Args:
            count: 获取的K线数量，None表示全部
            
        Returns:
            K线列表
        """
        if count is None:
            return list(self.klines)
        else:
            return list(self.klines)[-count:]
    
    def get_summary(self) -> Dict:
        """
        获取K线统计摘要
        
        Returns:
            统计信息字典
        """
        if len(self.klines) == 0:
            return {
                'total_klines': 0,
                'trend': 'unknown',
                'price_change': 0,
                'price_change_pct': 0
            }
        
        first_kline = self.klines[0]
        last_kline = self.klines[-1]
        
        price_change = last_kline['close'] - first_kline['open']
        price_change_pct = (price_change / first_kline['open']) * 100 if first_kline['open'] > 0 else 0
        
        # 判断趋势
        if price_change_pct > 0.5:
            trend = 'uptrend'
        elif price_change_pct < -0.5:
            trend = 'downtrend'
        else:
            trend = 'sideways'
        
        # 计算最高和最低
        all_highs = [k['high'] for k in self.klines]
        all_lows = [k['low'] for k in self.klines]
        period_high = max(all_highs)
        period_low = min(all_lows)
        
        return {
            'total_klines': len(self.klines),
            'trend': trend,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'period_high': period_high,
            'period_low': period_low,
            'first_price': first_kline['open'],
            'last_price': last_kline['close']
        }
    
    def calculate_support_resistance(self) -> Dict:
        """
        计算支撑位和阻力位
        
        Returns:
            支撑和阻力位字典
        """
        if len(self.klines) < 3:
            return {'support': None, 'resistance': None}
        
        # 简单方法：使用最近的局部低点作为支撑，局部高点作为阻力
        lows = [k['low'] for k in self.klines]
        highs = [k['high'] for k in self.klines]
        
        # 最近的支撑位（最近几根K线的最低点）
        support = min(lows[-5:]) if len(lows) >= 5 else min(lows)
        
        # 最近的阻力位（最近几根K线的最高点）
        resistance = max(highs[-5:]) if len(highs) >= 5 else max(highs)
        
        return {
            'support': support,
            'resistance': resistance
        }
    
    def format_for_prompt(self, max_rows: int = 16) -> str:
        """
        格式化K线数据用于 AI prompt
        
        Args:
            max_rows: 最大显示行数
            
        Returns:
            格式化的字符串
        """
        klines = self.get_klines(max_rows)
        
        if len(klines) == 0:
            return "暂无历史K线数据"
        
        lines = []
        lines.append("时间    开盘     最高     最低     收盘     涨跌")
        lines.append("─" * 50)
        
        for kline in klines:
            time_str = kline['time'].strftime('%H:%M')
            open_price = kline['open']
            high_price = kline['high']
            low_price = kline['low']
            close_price = kline['close']
            change_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
            
            change_symbol = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
            
            lines.append(f"{time_str}  {open_price:>7.0f}  {high_price:>7.0f}  "
                        f"{low_price:>7.0f}  {close_price:>7.0f}  {change_symbol}{change_pct:>+6.2f}%")
        
        # 添加统计摘要
        summary = self.get_summary()
        sr = self.calculate_support_resistance()
        
        lines.append("─" * 50)
        lines.append(f"周期统计：{summary['total_klines']}根K线（{summary['total_klines']*15}分钟）")
        lines.append(f"整体趋势：{'上涨' if summary['trend'] == 'uptrend' else '下跌' if summary['trend'] == 'downtrend' else '震荡'}")
        lines.append(f"价格变化：{summary['price_change']:+.0f} ({summary['price_change_pct']:+.2f}%)")
        lines.append(f"区间高点：${summary['period_high']:,.0f}")
        lines.append(f"区间低点：${summary['period_low']:,.0f}")
        
        if sr['support'] and sr['resistance']:
            lines.append(f"支撑位：${sr['support']:,.0f}")
            lines.append(f"阻力位：${sr['resistance']:,.0f}")
        
        return "\n".join(lines)

