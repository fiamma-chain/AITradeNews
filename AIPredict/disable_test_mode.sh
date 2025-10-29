#!/bin/bash
# 禁用测试模式 - 恢复正常的增量检测

echo "🔧 禁用新闻交易测试模式..."

# 取消环境变量
unset NEWS_TRADING_TEST_MODE

# 重启服务
echo "🔄 重启服务..."
pkill -f consensus_arena_multiplatform
sleep 2

cd /Users/cyimon/Work/Dev/AIMarket/AIPredict
python3 consensus_arena_multiplatform.py > /tmp/ai_trading.log 2>&1 &
echo $! > /tmp/ai_trading.pid

sleep 3
echo "✅ 测试模式已禁用，恢复正常模式"
echo "📊 查看日志: tail -f /tmp/ai_trading.log"

