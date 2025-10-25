# 消息交易性能测试 - 快速启动

## ✅ 已完成修改

1. ✅ 添加配置开关（禁用常规交易）
2. ✅ 增强时间记录（分析/平仓/开仓/总计）
3. ✅ 创建测试脚本
4. ✅ 优化性能指标输出

---

## 🚀 启动步骤

### 1. 手动编辑`.env`文件

```bash
nano .env
```

添加/修改以下内容：

```env
# 禁用常规交易（性能测试）
ENABLE_CONSENSUS_TRADING=False
ENABLE_INDIVIDUAL_TRADING=False

# 启用消息交易
NEWS_TRADING_ENABLED=True
NEWS_TRADING_AIS=claude,gpt,deepseek
```

保存并退出（Ctrl+X, Y, Enter）

### 2. 启动主系统

```bash
python consensus_arena_multiplatform.py
```

**预期输出：**
```
🚫 常规交易已禁用（仅消息驱动模式）
📢 系统已初始化，等待消息触发...
```

### 3. 另开终端，启动消息交易

```bash
curl -X POST http://localhost:46000/api/news_trading/start
```

**预期输出：**
```json
{
  "message": "消息交易系统已启动",
  "active_ais": ["Claude", "GPT-4", "DeepSeek"],
  "listeners": 4
}
```

### 4. 提交测试消息

```bash
# 方式1：单个测试
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/btc-listing&coin=BTC"

# 方式2：批量测试（使用脚本）
./test_news_trading.sh
```

### 5. 查看实时日志

```bash
tail -f logs/server-*.log | grep -E "⏱️|✨|📬|🤖|✅"
```

---

## 📊 性能指标

系统会输出以下指标：

```
⏱️  [Claude] BTC 处理完成
   分析耗时: 2.34s
   平仓耗时: 0.00s
   开仓耗时: 1.56s
   ✨ 总耗时: 3.90s  ← 目标: < 5s
```

### 目标性能

- ✅ **总耗时** < 5秒
- ✅ **AI分析** < 3秒  
- ✅ **开仓** < 2秒

---

## 🔍 验证项

### 1. 真实下单

查看Hyperliquid和Aster平台是否有新订单

### 2. 参数正确

- **杠杆**: 10-40x（AI根据消息动态调整）
- **保证金**: 50-500 USDT
- **方向**: Long/Short（AI判断）

### 3. 平仓逻辑

如果AI已有该币种仓位，应先看到平仓日志，再看到开仓日志

---

## 📝 测试币种建议

以Aster已支持的币种为准：

1. **BTC** - 最常见
2. **ETH** - 第二大
3. **SOL** - 热门新币

确保这些币种在`news_trading/config.py`的`COIN_MAPPING`中已配置。

---

## ⚠️ 注意事项

1. **账户余额** - 确保3个AI账户有足够余额（建议每个>100U）
2. **网络延迟** - AI调用需要网络，请确保网络稳定
3. **真实下单** - 这是真实交易，会消耗资金！
4. **冷却时间** - 同币种60秒内不会重复交易

---

## 🛠️ 故障排查

### 问题1：启动后提示"Arena未启动"

**解决**：主系统未正常初始化，检查日志

### 问题2：AI不参与交易

**解决**：
1. 检查`.env`中`NEWS_TRADING_AIS`配置
2. 检查对应AI的API Key是否配置
3. 查看日志确认AI是否加载成功

### 问题3：总耗时>5秒

**可能原因**：
1. AI API调用慢（网络问题）
2. 交易所API响应慢
3. 并发处理有问题

查看详细日志分析各阶段耗时。

---

## 📚 相关文档

- [完整使用指南](NEWS_TRADING_GUIDE.md)
- [性能测试说明](NEWS_TRADING_PERFORMANCE_TEST.md)
- [实现总结](NEWS_TRADING_SUMMARY.md)

**准备好了就开始测试吧！** 🚀

