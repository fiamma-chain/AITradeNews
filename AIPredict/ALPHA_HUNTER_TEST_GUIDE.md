# 🎯 Alpha Hunter 测试指南

## ✅ 当前实现状态

**完整的 Alpha Hunter 功能已实现！** 可以进行端到端测试。

---

## 📋 测试前准备

### 1. 环境要求

- ✅ Hyperliquid 测试网账户（有余额）
- ✅ Hyperliquid 私钥（用于授权 Agent）
- ✅ 已添加并激活监控的币种
- ✅ 新闻监听系统正常运行

### 2. 检查配置

```bash
# 检查环境变量
cat .env | grep -E "HYPERLIQUID|NEWS_TRADING"

# 确认以下配置：
HYPERLIQUID_TESTNET=true
NEWS_TRADING_AIS=grok
ALLOWED_TRADING_SYMBOLS=<你的测试币种>
```

---

## 🚀 测试流程

### Step 1: 启动系统

```bash
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
make run

# 或前台运行（查看日志）
make dev
```

### Step 2: 访问前端

打开浏览器访问: **http://localhost:46000**

### Step 3: 添加测试币种（如果还没有）

1. 点击 **"Submit New Coin"** 按钮
2. 填写币种信息：
   - Symbol: 例如 `BTC`
   - Name: 例如 `Bitcoin`
   - Project Type: 选择类型
   - Twitter Link: 项目 Twitter
   - Trading Link: 交易链接
3. 提交后币种卡片会出现

### Step 4: 激活币种监控

1. 找到你要测试的币种卡片
2. 点击 **"▶ Monitor"** 按钮
3. 按钮变为红色 **"⏹ Stop"**，徽章显示 **"Live"**

### Step 5: 使用 Alpha Hunter

在 **"Alpha Hunter"** 卡片中：

#### 1️⃣ 输入 Hyperliquid 私钥
```
示例: 0x1234567890abcdef...
```
⚠️ **注意**：
- 私钥仅用于调用 `approve_agent` 接口
- 不会被存储，仅用于生成 Agent
- 建议使用测试网账户

#### 2️⃣ 选择币种
从下拉列表选择已激活监控的币种（例如 `BTC`）

#### 3️⃣ 输入投资金额
```
示例: 100 USDT
```
这是每次交易的**保证金**（逐仓模式）

#### 4️⃣ 点击 "Approve Agent & Start"

系统会执行以下步骤：
- 🔑 调用 Hyperliquid `approve_agent`（生成并授权 Agent）
- 📡 注册配置到后端
- 🎯 启动监控

---

## 📊 测试预期结果

### 成功提示

如果一切正常，你会看到：

```
✅ Alpha Hunter Activated!

Coin: BTC
Margin: 100 USDT (per trade)
Your Address: 0x1234...5678
Agent Address: 0xabcd...ef01
Account Balance: 1000 USDC

🤖 AI Agent (Grok-4) will now automatically:
• Monitor BTC listing news
• Analyze with AI confidence scoring
• Execute trades (10-50x leverage)
• Use isolated margin per coin

📊 You can monitor performance in real-time below.
```

### Live Activity Feed

在 **"实时事件"** 卡片中会显示：
```
🎯 Alpha Hunter activated for BTC with $100 margin by 0x1234...5678
```

---

## 🔍 监控 AI 交易

### 触发交易

Alpha Hunter 会在以下情况自动交易：

1. **新闻监听器检测到相关币种**
   - Binance Spot 上市
   - Binance Futures 上市
   - 其他交易所上市

2. **Grok AI 分析新闻**
   - 判断是否交易（BUY/SELL/HOLD）
   - 决定信心度（confidence）
   - 决定杠杆（10-50x）

3. **Agent 自动下单**
   - 使用授权的 Agent 私钥
   - 在 Hyperliquid 上执行市价单
   - 逐仓模式，使用配置的保证金

### 查看日志

**后端日志（推荐）：**
```bash
tail -f nohup.out

# 关键日志：
# ✅ Agent 授权成功: 0xabcd...
# 📢 Alpha Hunter 处理新闻触发
# 🤖 Grok AI 决策: BUY
# ✅ Alpha Hunter 订单执行成功
```

**前端日志（浏览器 Console）：**
```javascript
console.log('✅ Agent approved:', agentInfo);
console.log('✅ Registration successful');
console.log('✅ Monitoring started');
```

---

## 🧪 模拟测试（手动触发）

如果想立即测试而不等待真实新闻：

### 方案 A: 提交测试链接

1. 在 **"News Sources"** 区域点击 **"Submit Link"**
2. 输入一个包含你监控币种的 Binance 公告链接
3. 系统会自动分析并触发 Alpha Hunter

### 方案 B: 使用测试模式

```bash
# 在 .env 中添加
NEWS_TRADING_TEST_MODE=true

# 重启系统
make stop
make run
```

测试模式下，所有已上市的币种都会被视为"新上市"，触发 AI 分析。

---

## 📈 验证交易结果

### 1. 检查 Hyperliquid 持仓

访问 Hyperliquid 测试网：
```
https://app.hyperliquid-testnet.xyz/
```

使用你的**主账户地址**登录，查看持仓。

**注意**：订单是由 Agent 下的，但持仓归属于你的主账户。

### 2. 查看后端数据

```bash
# 查看 Alpha Hunter 状态
curl http://localhost:46000/api/alpha_hunter/status?user_address=0x你的地址
```

### 3. 前端实时更新

- **Live Activity Feed**: 显示交易消息
- **K线图**: 显示交易标记（🚀 新闻驱动交易）

---

## ⚠️ 常见问题

### Q1: "Failed to approve agent on Hyperliquid"

**原因**：私钥错误或 Hyperliquid API 调用失败

**解决**：
1. 确认私钥格式正确（以 `0x` 开头）
2. 确认账户在测试网有余额
3. 检查网络连接

### Q2: "Registration failed"

**原因**：Agent 客户端创建失败

**解决**：
1. 查看后端日志：`tail -f nohup.out`
2. 确认 Agent 私钥有效
3. 确认账户余额充足

### Q3: "Failed to start monitoring"

**原因**：监控系统未初始化

**解决**：
1. 确认至少有一个币种在监控中
2. 重启系统：`make stop && make run`

### Q4: AI 不执行交易

**原因**：AI 判断为 HOLD 或新闻不相关

**解决**：
1. 查看日志：AI 的决策和原因
2. 调整 AI prompt（`news_trading/news_analyzer.py`）
3. 使用更明确的新闻测试

### Q5: 订单失败

**原因**：杠杆/保证金/精度问题

**解决**：
1. 检查 Hyperliquid 该币种的最大杠杆
2. 确认保证金充足
3. 查看 `trading/precision_config.py` 精度配置

---

## 🔐 安全提醒

1. **私钥安全**
   - ✅ 私钥仅用于调用 `approve_agent`
   - ✅ 不会被存储在前端或后端数据库
   - ⚠️  但会在 HTTP 请求中传输（建议 HTTPS）
   - ⚠️  Agent 私钥会存储在后端内存中

2. **Agent 权限**
   - ✅ Agent 只能交易，不能转账
   - ✅ Agent 不能提现
   - ✅ 逐仓模式，每个币种独立保证金

3. **风险控制**
   - ⚠️  AI 可能做出错误决策
   - ⚠️  高杠杆有清算风险
   - ⚠️  建议小额测试

---

## 📝 测试检查清单

- [ ] 系统成功启动
- [ ] 前端页面正常访问
- [ ] 币种已添加并激活监控
- [ ] Alpha Hunter 成功授权 Agent
- [ ] Alpha Hunter 注册成功
- [ ] 监控状态显示为活跃
- [ ] 新闻触发 AI 分析
- [ ] AI 返回交易决策
- [ ] Agent 成功下单
- [ ] Hyperliquid 显示持仓
- [ ] 前端实时更新

---

## 🎯 下一步

测试完成后，你可以：

1. **扩展监控币种**
   - 添加更多币种
   - 为每个币种配置不同保证金

2. **优化 AI 策略**
   - 调整 `news_trading/news_analyzer.py` 的 prompt
   - 测试不同的信心阈值

3. **增强功能**
   - 持仓管理界面
   - 实时 PnL 计算
   - 多用户支持
   - 加密存储 Agent 私钥

---

## 📞 遇到问题？

查看详细文档：
- `ALPHA_HUNTER_IMPLEMENTATION.md` - 实现细节
- 后端日志：`tail -f nohup.out`
- 前端 Console：浏览器开发者工具

---

**祝测试顺利！🚀**

