# 消息交易系统性能测试配置

## 配置说明

编辑`.env`文件，添加以下配置：

```env
# 禁用常规交易（性能测试）
ENABLE_CONSENSUS_TRADING=False
ENABLE_INDIVIDUAL_TRADING=False

# 启用消息交易
NEWS_TRADING_ENABLED=True
NEWS_TRADING_AIS=claude,gpt,deepseek
```

## 测试场景

### 场景1：历史上币消息测试

模拟真实上币场景，从Aster已支持的币种中选择，测试AI响应速度。

```bash
# 测试 SOL（假设币安刚宣布上线）
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/sol-listing&coin=SOL"

# 测试 ETH
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/eth-listing&coin=ETH"

# 测试 BTC
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/btc-listing&coin=BTC"
```

### 场景2：真实新闻链接

```bash
# 使用真实的币安公告链接
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/binance-will-list-bitcoin-cash-abc-bch-ba9fca8e9b8f401697cb15bb2b2dc48e&coin=BTC"
```

## 性能指标

系统会自动记录以下时间：

1. **分析耗时** - AI分析消息用时
2. **平仓耗时** - 关闭现有仓位用时（如果有）
3. **开仓耗时** - 在HL+Aster开新仓用时
4. **总耗时** - 从收到消息到完成所有操作

### 日志示例

```
📬 [消息交易] 收到上币消息: BTC (来源: user_submitted)
🤖 准备让 3 个AI分析...
🤖 [Claude] 开始分析消息: BTC
✅ [Claude] 分析完成: long 30x, 信心度 85.0% (耗时: 2.34s)
🚀 [Claude] [Hyperliquid] 准备开仓 BTC
✅ [Claude] [Hyperliquid] 开仓成功
🚀 [Claude] [Aster] 准备开仓 BTC
✅ [Claude] [Aster] 开仓成功
⏱️  [Claude] BTC 处理完成
   分析耗时: 2.34s
   平仓耗时: 0.00s
   开仓耗时: 1.56s
   ✨ 总耗时: 3.90s
```

## 测试目标

- ✅ 总耗时 < 5秒
- ✅ AI分析 < 3秒
- ✅ 开仓 < 2秒
- ✅ 真实下单成功
- ✅ 参数正确（杠杆、保证金、方向）

## 注意事项

1. 确保独立AI账户有足够余额
2. 测试时系统不会运行常规5分钟交易循环
3. 只有配置的AI（如3个）会响应
4. 每个AI用自己的账户，互不影响

