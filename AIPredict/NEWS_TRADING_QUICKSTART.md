# 消息驱动交易 - 快速开始

## 📦 第一步：安装依赖

```bash
pip install beautifulsoup4
```

## ⚙️ 第二步：配置`.env`

手动编辑`.env`文件，添加/修改以下两行：

```env
NEWS_TRADING_ENABLED=True
NEWS_TRADING_AIS=claude,gpt,deepseek
```

**说明**：
- 从6个AI中选择要参与消息交易的AI
- 可选：`deepseek`, `claude`, `grok`, `gpt`, `gemini`, `qwen`

## 🚀 第三步：启动

```bash
# 1. 启动主系统
python consensus_arena_multiplatform.py

# 2. 另开终端，启动消息交易
curl -X POST http://localhost:46000/api/news_trading/start
```

## ✅ 验证

```bash
# 查看状态
curl http://localhost:46000/api/news_trading/status

# 应该返回：
# {
#   "running": true,
#   "active_ais": ["Claude", "GPT-4", "DeepSeek"],
#   "listeners": 4
# }
```

## 📥 用户提交消息（可选）

```bash
curl -X POST "http://localhost:46000/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/xxx&coin=BTC"
```

## 📊 监控日志

```bash
tail -f logs/server-*.log | grep -E "📬|🤖|✅|🚀"
```

---

## 🎯 工作原理

```
消息到达（自动/用户提交）
    ↓
配置的3个AI并发分析
    ↓
每个AI用自己的账户
    ↓
有仓位 → 先平仓
    ↓
在HL+Aster开新仓
```

---

## 📚 详细文档

- 完整使用指南：[NEWS_TRADING_GUIDE.md](./NEWS_TRADING_GUIDE.md)
- 实现总结：[NEWS_TRADING_SUMMARY.md](./NEWS_TRADING_SUMMARY.md)

**就这么简单！** 🚀

