# 交易精度配置说明

## 概述

本系统使用统一的精度配置模块 `trading/precision_config.py`，确保所有平台的下单参数精度与平台要求完全匹配。

## 平台精度要求

### Hyperliquid (HL)

**BTC 交易对**:
- **数量精度**: 5位小数 (0.00001)
- **价格精度**: 整数 (1)
- **数量步长**: 0.00001
- **价格步长**: 1
- **最小数量**: 0.00001 BTC
- **最小名义价值**: 10 USD

**ETH 交易对**:
- **数量精度**: 4位小数 (0.0001)
- **价格精度**: 整数 (1)
- **数量步长**: 0.0001
- **价格步长**: 1
- **最小数量**: 0.0001 ETH
- **最小名义价值**: 10 USD

### Aster (AS)

**BTC 交易对**:
- **数量精度**: 3位小数 (0.001)
- **价格精度**: 1位小数 (0.1)
- **数量步长**: 0.001
- **价格步长**: 0.1
- **最小数量**: 0.001 BTC
- **最小名义价值**: 5 USDT

**ETH 交易对**:
- **数量精度**: 3位小数 (0.001)
- **价格精度**: 2位小数 (0.01)
- **数量步长**: 0.001
- **价格步长**: 0.01
- **最小数量**: 0.001 ETH
- **最小名义价值**: 5 USDT

## 精度处理逻辑

### 数量处理

1. **开仓订单**: 使用 `ROUND_DOWN` (向下取整)
   - 确保不会因余额不足导致订单失败
   - 例: 0.001234 → 0.00123 (Aster) 或 0.00123 (Hyperliquid)

2. **平仓订单**: 使用 `ROUND_HALF_UP` (四舍五入)
   - 确保完全平掉持仓，避免残余
   - 例: 0.001234 → 0.001 (Aster) 或 0.00123 (Hyperliquid)

### 价格处理

- **Hyperliquid BTC**: 取整到最近的整数
  - 例: 108423.7 → 108424

- **Aster BTC**: 取整到最近的 0.1
  - 例: 108423.7 → 108423.7

- **市价单**: 自动获取盘口价格并按精度要求格式化

### 订单验证

系统会自动验证：
1. **数量验证**: 确保不小于最小数量
2. **名义价值验证**: 确保 `数量 × 价格` 不小于最小名义价值
3. **精度验证**: 确保数量和价格符合步长要求

如果验证失败，订单将被拒绝并记录错误日志。

## 代码示例

### Aster 下单

```python
from trading.precision_config import precision_config

# 格式化数量
size_rounded, _ = precision_config.format_aster_quantity(
    "BTC", 0.001234, round_down=True
)
# 结果: 0.001

# 格式化价格
price_rounded, _ = precision_config.format_aster_price(
    "BTC", 108423.7
)
# 结果: 108423.7

# 验证订单
is_valid, error_msg = precision_config.validate_aster_order(
    "BTC", size_rounded, price_rounded
)
# 结果: (True, "")
```

### Hyperliquid 下单

```python
from trading.precision_config import precision_config

# 格式化数量
size_rounded, _ = precision_config.format_hyperliquid_quantity(
    "BTC", 0.001234, round_down=True
)
# 结果: 0.00123

# 格式化价格
price_rounded, _ = precision_config.format_hyperliquid_price(
    "BTC", 108423.7
)
# 结果: 108424

# 验证订单
is_valid, error_msg = precision_config.validate_hyperliquid_order(
    "BTC", size_rounded, price_rounded
)
# 结果: (True, "")
```

## 常见错误及解决

### Aster: "Precision is over the maximum defined for this asset"

**原因**: 价格或数量的小数位数超过平台要求

**解决**: 
- BTC 价格必须是 0.1 的倍数 (例: 108423.7 ✅, 108423.71 ❌)
- BTC 数量必须是 0.001 的倍数 (例: 0.001 ✅, 0.0001 ❌)

### Aster: "Quantity less than zero" 或 "Quantity too small"

**原因**: 数量向下取整后小于最小值

**解决**: 
- 确保订单金额至少为 `0.001 × 当前价格`
- BTC 最小数量为 0.001，按当前价格约 $108
- 建议订单金额至少 $150

### Hyperliquid: "Order could not immediately match"

**原因**: 市价单在当前盘口无法立即成交

**解决**: 
- 系统会自动使用盘口价格
- 如果使用 `Ioc` (立即成交或取消)，可能因流动性不足失败
- 平仓订单自动使用 `Ioc`，开仓订单使用 `Gtc`

### 通用: "Notional value too small"

**原因**: 订单的名义价值 (`数量 × 价格`) 小于最小要求

**解决**: 
- Hyperliquid 最小名义价值: $10
- Aster 最小名义价值: $5
- 增加订单数量或选择价格更高的币种

## 配置文件位置

- **精度配置模块**: `trading/precision_config.py`
- **Hyperliquid 客户端**: `trading/hyperliquid/client.py`
- **Aster 客户端**: `trading/aster/client.py`

## 更新精度配置

如需添加新币种或更新精度，修改 `trading/precision_config.py` 中的字典：

```python
ASTER_PRECISION = {
    "NEW_COIN": {
        "quantity_precision": 3,
        "price_precision": 2,
        "quantity_step": "0.001",
        "price_tick": "0.01",
        "min_quantity": "0.001",
        "min_notional": "5"
    }
}
```

## 测试精度

可以通过以下脚本测试精度配置：

```python
python3 -c "
from trading.precision_config import precision_config

# 测试 Aster BTC
qty, _ = precision_config.format_aster_quantity('BTC', 0.001234)
price, _ = precision_config.format_aster_price('BTC', 108423.789)
valid, msg = precision_config.validate_aster_order('BTC', qty, price)

print(f'Aster BTC:')
print(f'  数量: 0.001234 → {qty}')
print(f'  价格: 108423.789 → {price}')
print(f'  验证: {valid} {msg}')
print()

# 测试 Hyperliquid BTC
qty, _ = precision_config.format_hyperliquid_quantity('BTC', 0.001234)
price, _ = precision_config.format_hyperliquid_price('BTC', 108423.789)
valid, msg = precision_config.validate_hyperliquid_order('BTC', qty, price)

print(f'Hyperliquid BTC:')
print(f'  数量: 0.001234 → {qty}')
print(f'  价格: 108423.789 → {price}')
print(f'  验证: {valid} {msg}')
"
```

## 总结

✅ **已实现**:
- 统一的精度配置管理
- 自动精度格式化和验证
- 开仓/平仓的不同取整策略
- 详细的错误提示和日志

✅ **精度匹配**:
- Hyperliquid: ✅ 数量5位小数，价格整数
- Aster: ✅ 数量3位小数，价格1位小数

✅ **下单保证**:
- 不会因精度问题导致订单失败
- 自动验证订单参数的合法性
- 清晰的错误信息便于调试

