#!/bin/bash
# 消息交易系统测试脚本

echo "🚀 消息交易系统性能测试"
echo "================================"

# API地址
API_URL="http://localhost:46000"

# 测试消息提交
test_message() {
    local coin=$1
    local message=$2
    
    echo ""
    echo "📬 测试币种: $coin"
    echo "消息: $message"
    echo "⏰ 开始时间: $(date +%H:%M:%S.%N)"
    
    # 提交消息（使用真实的币安公告链接）
    response=$(curl -s -X POST "${API_URL}/api/news_trading/submit?url=https://www.binance.com/en/support/announcement/binance-will-list-${coin,,}-listing&coin=$coin")
    
    echo "响应: $response"
    echo "⏰ 结束时间: $(date +%H:%M:%S.%N)"
    echo "--------------------------------"
}

# 1. 检查系统状态
echo ""
echo "1️⃣ 检查系统状态..."
status=$(curl -s "${API_URL}/api/news_trading/status")
echo "$status"

if [[ $status == *'"running":true'* ]]; then
    echo "✅ 消息交易系统运行中"
else
    echo "❌ 消息交易系统未运行"
    echo "请先启动: curl -X POST ${API_URL}/api/news_trading/start"
    exit 1
fi

# 2. 测试不同币种
echo ""
echo "2️⃣ 开始测试..."

# 测试BTC
test_message "BTC" "Binance will list Bitcoin (BTC)"

# 等待一段时间
sleep 10

# 测试ETH
test_message "ETH" "Binance will list Ethereum (ETH)"

# 等待一段时间
sleep 10

# 测试SOL
test_message "SOL" "Binance will list Solana (SOL)"

echo ""
echo "✅ 测试完成！"
echo "请查看日志: tail -f logs/server-*.log"

