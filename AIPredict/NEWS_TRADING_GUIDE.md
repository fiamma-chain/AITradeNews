# 消息驱动交易系统使用指南

## 🎯 系统特点

### ✅ **简化版设计**
1. **复用现有账户** - 不需要新私钥，使用6个独立AI的现有账户
2. **灵活配置** - 只启用你想要的AI（如 claude, gpt, deepseek）
3. **去中心化触发** - 自动监听 + 用户提交，双重触发机制
4. **智能平仓** - 有仓位时自动先平仓再开新仓

---

## 📋 **配置步骤**

### 1. 编辑`.env`文件

```bash
# 启用消息交易
NEWS_TRADING_ENABLED=True

# 选择参与的AI（从以下6个中选择）
# deepseek, claude, grok, gpt, gemini, qwen
NEWS_TRADING_AIS=claude,gpt,deepseek
```

**注意**：
- 只有配置在`NEWS_TRADING_AIS`中的AI会参与消息交易
- 必须确保这些AI在`INDIVIDUAL_XXX_PRIVATE_KEY`中已配置
- 每个AI会用自己的账户独立下单

---

## 🚀 **使用方法**

### 方式1：API启动

```bash
# 1. 启动主系统
python consensus_arena_multiplatform.py

# 2. 启动消息交易（通过API）
curl -X POST http://localhost:46000/api/news_trading/start

# 3. 查看状态
curl http://localhost:46000/api/news_trading/status

# 4. 停止
curl -X POST http://localhost:46000/api/news_trading/stop
```

### 方式2：前端用户提交

**用户可以在前端提交消息**（待实现前端UI）：

```bash
# 提交上币消息
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://example.com/listing-news&coin=BTC"
```

参数：
- `url`: 消息链接
- `coin`: 币种符号（如 BTC, ETH, SOL）

---

## 📊 **工作流程**

### 自动监听模式

```
币安/Upbit发布上币公告
    ↓
系统自动捕获
    ↓
配置的3个AI并发分析
    ↓
每个AI独立决策
    ↓
用自己的账户在HL+Aster下单
```

### 用户提交模式

```
用户提交URL + 币种
    ↓
系统爬取网页内容
    ↓
配置的3个AI并发分析
    ↓
每个AI独立决策
    ↓
用自己的账户在HL+Aster下单
```

### 平仓逻辑

```
新消息到达 → 检查该AI是否已有该币种仓位
   ↓ 有
先平掉现有仓位 → 再开新仓
   ↓ 无
直接开新仓
```

---

## 🤖 **AI决策流程**

每个AI独立分析消息，决定：

1. **是否交易** - 基于消息可靠性、币种类型
2. **方向** - Long/Short
3. **杠杆** - 10-40x（动态调整）
4. **保证金** - 50-500 USDT
5. **止盈止损** - 10-50% / 5-20%

---

## 📝 **示例场景**

### 场景1：币安发布新币上线公告

```
1. 币安公告：MONAD (MON) 将上线现货交易
2. 系统自动捕获消息
3. Claude分析：建议做多，30x杠杆，$200保证金
4. GPT分析：建议做多，25x杠杆，$150保证金
5. DeepSeek分析：不建议交易（信心度不足）
6. Claude和GPT各自用自己的账户开仓
7. DeepSeek不参与
```

### 场景2：用户提交推特消息

```
1. 用户在前端提交：
   URL: https://twitter.com/binance/status/xxx
   Coin: SOL
2. 系统爬取推特内容
3. 3个AI并发分析
4. 根据分析结果各自下单
```

### 场景3：已有仓位时的处理

```
1. Claude持有BTC多单
2. 新消息：BTC重大利空
3. Claude分析：建议做空
4. 系统自动：
   - 先平掉BTC多单
   - 再开BTC空单
```

---

## ⚙️ **配置币种映射**

如果要支持新币种，编辑`news_trading/config.py`：

```python
COIN_MAPPING = {
    # 老币
    "BTC": "BTC",
    "BITCOIN": "BTC",
    
    # 新币（添加这里）
    "MONAD": "MON",
    "MON": "MON",
    "MEGAETH": "MEGA",
}
```

---

## 🔍 **监控日志**

关键日志标识：

- `📬` - 收到上币消息
- `🤖` - AI开始分析
- `✅` - 分析完成/交易成功
- `📤` - 平掉现有仓位
- `🚀` - 开新仓
- `⚠️` - 警告/跳过
- `❌` - 错误

示例：
```
📬 [消息交易] 收到上币消息: MON (来源: binance_spot)
🤖 准备让 3 个AI分析...
🤖 [Claude] 开始分析消息: MON
✅ [Claude] 分析完成: long 30x, 信心度 85.0%
📤 [Claude] [Hyperliquid] 存在 MON 仓位，先平仓
✅ [Claude] [Hyperliquid] MON 平仓完成
🚀 [Claude] [Hyperliquid] 准备开仓 MON
✅ [Claude] [Hyperliquid] 开仓成功
```

---

## ⚠️ **注意事项**

1. **账户余额** - 确保独立AI账户有足够余额
2. **API限流** - 监听器每30-60秒轮询一次，避免频繁请求
3. **币种支持** - 只交易`COIN_MAPPING`中配置的币种
4. **风险提示** - 最大40x杠杆，请充分了解风险
5. **并发处理** - 3个AI同时分析，不会互相影响

---

## 🛠️ **故障排查**

### 问题：启动失败，提示"Arena未启动"
**解决**：必须先启动主系统，确保独立AI已初始化

### 问题：某个AI不参与交易
**解决**：检查`.env`中该AI的API Key是否配置

### 问题：用户提交后没有反应
**解决**：
1. 检查币种是否在`COIN_MAPPING`中
2. 查看日志，确认URL能否正常爬取
3. 确认AI分析是否通过（信心度>60%）

### 问题：平仓失败
**解决**：可能是网络问题或交易所限制，查看详细日志

---

## 📚 **API参考**

### POST /api/news_trading/start
启动消息交易系统

**返回**：
```json
{
  "message": "消息交易系统已启动",
  "active_ais": ["Claude", "GPT-4", "DeepSeek"],
  "listeners": 4
}
```

### POST /api/news_trading/submit
用户提交消息

**参数**：
- `url`: 消息URL
- `coin`: 币种符号

**返回**：
```json
{
  "success": true,
  "message": "消息已提交，3个AI正在分析",
  "coin": "BTC",
  "url": "https://...",
  "content_preview": "Binance will list..."
}
```

### GET /api/news_trading/status
查询系统状态

**返回**：
```json
{
  "running": true,
  "active_ais": ["Claude", "GPT-4", "DeepSeek"],
  "listeners": 4
}
```

---

## 🎨 **前端集成（待实现）**

建议添加一个消息提交表单：

```html
<div class="news-submit-form">
  <h3>📥 提交上币消息</h3>
  <input type="url" placeholder="消息链接" id="news-url">
  <input type="text" placeholder="币种(如BTC)" id="news-coin">
  <button onclick="submitNews()">提交分析</button>
</div>

<script>
async function submitNews() {
  const url = document.getElementById('news-url').value;
  const coin = document.getElementById('news-coin').value;
  
  const response = await fetch(
    `/api/news_trading/submit?url=${encodeURIComponent(url)}&coin=${coin}`,
    {method: 'POST'}
  );
  
  const result = await response.json();
  alert(result.message);
}
</script>
```

---

## 🚀 **快速开始**

```bash
# 1. 编辑.env
nano .env
# 设置: NEWS_TRADING_ENABLED=True
# 设置: NEWS_TRADING_AIS=claude,gpt,deepseek

# 2. 启动系统
python consensus_arena_multiplatform.py

# 3. 另开终端，启动消息交易
curl -X POST http://localhost:46000/api/news_trading/start

# 4. 观察日志
tail -f logs/server-*.log | grep "消息交易"
```

就是这么简单！🎉

