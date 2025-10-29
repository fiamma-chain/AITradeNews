#!/bin/bash

echo "🔍 监控 ASTER 检测流程..."
echo "================================"
echo ""

while true; do
    clear
    echo "📊 ASTER 测试监控 - $(date '+%H:%M:%S')"
    echo "================================"
    echo ""
    
    # 1. 检查监听器状态
    echo "1️⃣ 监听器状态:"
    tail -50 /tmp/ai_trading.log | grep -E "binance_spot.*启动|获取到.*交易对|检测到.*ASTER" | tail -3
    echo ""
    
    # 2. 检查消息处理
    echo "2️⃣ 消息处理:"
    tail -50 /tmp/ai_trading.log | grep -E "ASTER|消息交易.*ASTER|发现监控币种" | tail -3
    echo ""
    
    # 3. 检查AI决策
    echo "3️⃣ AI决策:"
    tail -50 /tmp/ai_trading.log | grep -E "Grok.*ASTER|AI分析|决策" | tail -3
    echo ""
    
    # 4. 检查交易执行
    echo "4️⃣ 交易执行:"
    tail -50 /tmp/ai_trading.log | grep -E "开仓|平仓|Hyperliquid.*ASTER" | tail -3
    echo ""
    
    echo "================================"
    echo "按 Ctrl+C 停止监控"
    
    sleep 3
done

