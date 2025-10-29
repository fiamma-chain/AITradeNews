# 📊 新闻交易测试模式使用指南

## 🎯 测试模式说明

测试模式允许系统把**已上线的代币**当作**新上线的代币**来处理，从而触发完整的AI分析和交易流程。

### 正常模式 vs 测试模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| **正常模式** | 只检测增量（新上线的币种） | 生产环境 |
| **测试模式** | 把监控币种当作新上线处理 | 功能测试 |

---

## 🚀 方法一：通过环境变量启用（推荐）

### 1. 启用测试模式并重启服务

```bash
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
NEWS_TRADING_TEST_MODE=true python3 consensus_arena_multiplatform.py > /tmp/ai_trading.log 2>&1 &
echo $! > /tmp/ai_trading.pid
```

### 2. 前端操作

1. 打开浏览器：http://localhost:46000/
2. 点击要测试的币种（如 ASTER）的 **Monitor** 按钮
3. 等待 30 秒（Binance 轮询间隔）
4. 系统会检测到该币种并触发 AI 分析

### 3. 查看日志

```bash
tail -f /tmp/ai_trading.log | grep -E "ASTER|Grok|检测到|🆕|开多单|开空单"
```

### 4. 预期日志输出

```
🧪 [binance_spot] 测试模式已启用 - 将把监控币种视为新上线
🆕 [binance_spot] 检测到 1 个新交易对: {'ASTERUSDT'}
🎯 [binance_spot] 发现监控币种: ASTER
📊 [Grok] 开始分析消息: Binance Listed ASTER/USDT
💰 [Grok-Solo] 开多单: ASTER, 保证金: 150.0U, 杠杆: 20x
```

---

## 🧪 方法二：独立测试脚本（快速测试）

### 使用测试脚本

```bash
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
python3 test_coin_trading.py ASTER
```

### 脚本功能

- ✅ 直接触发 AI 分析流程
- ✅ 模拟币种上线消息
- ✅ 执行完整的下单流程
- ✅ 计时并输出详细日志

### 示例输出

```
================================================================================
🧪 测试币种上线流程: ASTER
================================================================================

📊 初始化Redis...
🤖 初始化Grok AI...
🔗 初始化Hyperliquid客户端...
💼 初始化自动交易器...
🌐 初始化多平台交易器...

📨 创建上线消息: ASTER
📡 初始化NewsHandler...
🧠 创建NewsAnalyzer...

🚀 开始处理上线消息...
   来源: binance_spot
   币种: ASTER
   标题: Binance Will List ASTER (Test)

⏱️  计时开始...
✅ 测试完成！
⏱️  总耗时: 2.34 秒

================================================================================
```

---

## 📋 测试多个币种

### 1. 测试 ASTER

```bash
python3 test_coin_trading.py ASTER
```

### 2. 测试 MON

```bash
python3 test_coin_trading.py MON
```

### 3. 测试 MEGA

```bash
python3 test_coin_trading.py MEGA
```

### 4. 测试 BTC

```bash
python3 test_coin_trading.py BTC
```

---

## ⚠️ 注意事项

### 1. 测试模式风险

- ⚠️ 测试模式会触发**真实下单**
- ⚠️ 确保账户有足够余额
- ⚠️ 建议在测试账户上运行

### 2. 如何避免真实下单

修改 `news_trading/news_handler.py`，在下单前添加：

```python
if settings.news_trading_test_mode:
    logger.info(f"🧪 [测试模式] 跳过真实下单")
    return
```

### 3. 禁用测试模式

重启服务时不设置环境变量：

```bash
pkill -f consensus_arena_multiplatform
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
python3 consensus_arena_multiplatform.py > /tmp/ai_trading.log 2>&1 &
```

或使用脚本：

```bash
./disable_test_mode.sh
```

---

## 🎯 测试检查清单

测试每个币种时，确认以下流程：

- [ ] 前端显示监控状态（绿色边框、Live 徽章）
- [ ] 日志显示检测到新交易对
- [ ] AI 完成分析并给出决策
- [ ] 系统计算保证金和杠杆
- [ ] 成功调用交易所 API
- [ ] K线图显示交易标记
- [ ] Live Activity 显示活动记录

---

## 📊 性能指标

| 阶段 | 目标时间 | 说明 |
|------|---------|------|
| 消息检测 | < 30s | Binance 轮询间隔 |
| AI 分析 | < 2s | Grok-4-fast 决策 |
| 下单执行 | < 1s | Hyperliquid API |
| **总耗时** | **< 35s** | 从检测到下单完成 |

---

## 🔧 故障排查

### 问题1：测试模式未生效

**原因**：环境变量未正确设置

**解决**：
```bash
# 检查环境变量
echo $NEWS_TRADING_TEST_MODE

# 确保在同一shell中启动服务
NEWS_TRADING_TEST_MODE=true python3 consensus_arena_multiplatform.py
```

### 问题2：未检测到币种

**原因**：币种未在 `ALLOWED_TRADING_SYMBOLS` 中

**解决**：
```bash
# 检查配置
grep ALLOWED_TRADING_SYMBOLS .env

# 添加币种
echo "ALLOWED_TRADING_SYMBOLS=BTC,ETH,SOL,ASTER,MON,MEGA" >> .env
```

### 问题3：AI 未下单

**原因**：信心度不足或其他逻辑判断

**解决**：查看完整日志
```bash
tail -100 /tmp/ai_trading.log | grep -A 20 "开始分析消息"
```

---

## 📞 联系支持

遇到问题？检查日志或联系开发团队。

