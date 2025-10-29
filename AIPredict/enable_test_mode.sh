#!/bin/bash
# 启用测试模式 - 把已上线的币种当作新上线处理

echo "🧪 启用新闻交易测试模式..."

# 设置环境变量
export NEWS_TRADING_TEST_MODE=true

# 重启服务
echo "🔄 重启服务..."
pkill -f consensus_arena_multiplatform
sleep 2

cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
python3 consensus_arena_multiplatform.py > /tmp/ai_trading.log 2>&1 &
echo $! > /tmp/ai_trading.pid

sleep 3
echo "✅ 测试模式已启用！"
echo "📊 查看日志: tail -f /tmp/ai_trading.log"
echo ""
echo "💡 测试流程："
echo "   1. 刷新浏览器: http://localhost:46000/"
echo "   2. 点击 ASTER 的 Monitor 按钮"
echo "   3. 系统会在30秒内检测到 ASTER 并触发交易"
echo "   4. 查看日志确认 Grok AI 的决策和下单过程"

