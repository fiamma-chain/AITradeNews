# 消息驱动交易 - 实战测试配置

## 🎯 测试目标
使用单一AI（Grok）进行消息驱动交易的实战测试，验证系统的可行性和性能。

---

## ⚙️ 当前配置

### **启用状态**
```bash
NEWS_TRADING_ENABLED=True                    # ✅ 已启用消息交易
NEWS_TRADING_AIS=grok                        # ✅ 仅使用Grok（响应最快）
ENABLE_CONSENSUS_TRADING=False               # ❌ 已禁用常规共识交易
ENABLE_INDIVIDUAL_TRADING=False              # ❌ 已禁用常规独立AI交易
```

### **AI性能指标**
```
Grok-4-Fast-Non-Reasoning:
├── 响应时间: 1.70s (极速)
├── 模型版本: grok-4-fast-non-reasoning
└── 适合场景: 高频消息驱动交易 ✅
```

---

## 📊 测试账户信息

### **使用账户**
```bash
# Grok独立交易账户（复用）
INDIVIDUAL_GROK_PRIVATE_KEY=0x18793a3bba9c73d0d62e1f430ebbf4857bad7fdd358ef9b5165a36567b0f70d4
```

### **交易平台**
```bash
# 双平台交易（消息交易会在两个平台同时下单）
ENABLED_PLATFORMS=hyperliquid,aster
```

---

## 🎲 交易参数配置

### **保证金策略**
```bash
# 基于信心度动态调整（10%-50%仓位）
AI_MIN_MARGIN=100.0              # 最小保证金
AI_MAX_MARGIN=200.0              # 最大保证金
```

**计算方式**：
```python
# 根据AI信心度决定仓位比例
position_size_pct = 0.1 + (confidence / 100) * 0.4
# 示例：
#   信心度60% → 仓位34% → margin = balance × 0.34
#   信心度80% → 仓位42% → margin = balance × 0.42
#   信心度100% → 仓位50% → margin = balance × 0.5
```

### **杠杆策略**
```bash
# AI动态决策（2x-5x）
AI_MAX_LEVERAGE=5.0
```

**计算方式**：
```python
leverage = 2.0 + ((confidence - 50) / 50) * 3.0
# 示例：
#   信心度50% → 2x杠杆
#   信心度75% → 3.5x杠杆
#   信心度100% → 5x杠杆
```

### **止盈止损**
```bash
# ⚠️ 当前配置（需要调整）
AI_STOP_LOSS_PCT=0.15            # 15%止损（价格波动）
AI_TAKE_PROFIT_PCT=0.30          # 30%止盈（价格波动）

# ⚠️ 问题：对于2-5x杠杆，这个配置过于宽松
# 建议调整为：
AI_STOP_LOSS_PCT=0.08            # 8%止损
AI_TAKE_PROFIT_PCT=0.15          # 15%止盈
```

---

## 📡 消息源配置

### **监听平台**
- ✅ 币安现货上币 (Binance Spot Listing)
- ✅ 币安合约上币 (Binance Futures Listing)
- ✅ 币安Alpha项目 (Binance Alpha Project)
- ✅ Upbit上币 (Upbit Listing)

### **支持币种**（可在 news_trading/config.py 中修改）
```python
SUPPORTED_COINS = ["BTC", "ETH", "SOL", "MON", "MEGA"]
```

---

## 🚀 启动流程

### **1. 启动主系统**
```bash
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
python consensus_arena_multiplatform.py
```

**预期输出**：
```
🚫 常规交易已禁用（仅消息驱动模式）
✅ 消息驱动交易已启用
📢 系统已初始化，等待消息触发...
```

### **2. 启动消息监听**
```bash
# 在另一个终端
curl -X POST http://localhost:46000/api/news_trading/start
```

**预期输出**：
```json
{
  "status": "started",
  "mode": "ai",
  "enabled_ais": ["grok"],
  "listeners": ["binance", "upbit"]
}
```

### **3. 检查系统状态**
```bash
curl http://localhost:46000/api/news_trading/status
```

---

## 🧪 测试方式

### **方式1：用户提交测试**
```bash
# 提交上币消息链接
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/xxx&coin=BTC"
```

### **方式2：等待真实消息**
系统会自动监听币安和Upbit的上币公告

---

## 📊 性能指标

### **目标延迟**
```
消息检测 → AI分析 → 订单完成 < 5秒
├── 消息检测: < 0.5s
├── AI分析 (Grok): ~1.7s
├── 平仓操作: ~0.5s
└── 开仓操作: ~1.0s
```

### **监控点**
- ✅ 消息接收时间戳
- ✅ AI分析开始/结束时间
- ✅ 订单提交/确认时间
- ✅ 总耗时

---

## ⚠️ 风险提示

### **实战测试注意事项**

1. **账户余额**
   - 建议使用小额测试账户（200-500U）
   - 避免使用主账户

2. **杠杆风险**
   - 当前最大5x杠杆
   - 价格波动20%可能爆仓
   - 密切监控仓位

3. **消息可靠性**
   - 并非所有上币消息都会带来正收益
   - Grok会根据消息可靠性评分
   - 建议观察多次后调整策略

4. **平台限制**
   - Hyperliquid: 最大50x杠杆，充足流动性
   - Aster: 最大125x杠杆，可能滑点较大

5. **止损设置**
   - 当前15%止损对5x杠杆可能过宽
   - 建议改为8%止损，15%止盈

---

## 📝 测试检查清单

在开始测试前，请确认：

- [ ] Grok API密钥配置正确
- [ ] 私钥配置正确且账户有充足余额
- [ ] 消息交易已启用（NEWS_TRADING_ENABLED=True）
- [ ] 常规交易已禁用（避免干扰）
- [ ] 监听器已启动
- [ ] 日志监控已就绪（logs/目录）
- [ ] 前端页面可访问（http://localhost:46000）

---

## 📈 测试后分析指标

### **成功率指标**
- 消息检测准确率
- AI判断准确率（做多/做空）
- 订单成功率
- 盈亏比

### **性能指标**
- 平均响应时间
- 最快/最慢响应时间
- 系统稳定性

### **收益指标**
- 单笔盈亏
- 累计盈亏
- 胜率
- 最大回撤

---

## 🔧 调试工具

### **查看日志**
```bash
# 实时日志
tail -f logs/app.log

# 错误日志
grep "ERROR\|❌" logs/app.log

# 交易日志
grep "开仓\|平仓\|止盈\|止损" logs/app.log
```

### **查看前端**
```
http://localhost:46000
```

---

## 📞 快速命令

```bash
# 启动系统
python consensus_arena_multiplatform.py

# 启动消息监听
curl -X POST http://localhost:46000/api/news_trading/start

# 停止消息监听
curl -X POST http://localhost:46000/api/news_trading/stop

# 查看状态
curl http://localhost:46000/api/news_trading/status

# 测试提交
curl -X POST "http://localhost:46000/api/news_trading/submit?url=xxx&coin=BTC"

# 停止系统
Ctrl+C 或 make stop
```

---

**准备就绪！祝测试顺利！** 🚀

