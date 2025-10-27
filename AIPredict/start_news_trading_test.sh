#!/bin/bash
# 消息驱动交易测试 - 快速启动脚本

echo "=========================================="
echo "🚀 消息驱动交易测试 - 启动脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查配置
echo "📋 检查配置..."
echo ""

# 检查消息交易是否启用
NEWS_ENABLED=$(grep "^NEWS_TRADING_ENABLED" .env | cut -d'=' -f2)
if [ "$NEWS_ENABLED" != "True" ]; then
    echo -e "${RED}❌ 错误: NEWS_TRADING_ENABLED 未启用${NC}"
    echo "   请在 .env 中设置: NEWS_TRADING_ENABLED=True"
    exit 1
fi
echo -e "${GREEN}✅ 消息交易已启用${NC}"

# 检查AI配置
NEWS_AIS=$(grep "^NEWS_TRADING_AIS" .env | cut -d'=' -f2 | awk '{print $1}')
echo -e "${GREEN}✅ 使用AI: $NEWS_AIS${NC}"

# 检查Grok API密钥
GROK_KEY=$(grep "^GROK_API_KEY" .env | cut -d'=' -f2)
if [ -z "$GROK_KEY" ] || [ "$GROK_KEY" = "your_grok_key_here" ]; then
    echo -e "${RED}❌ 错误: GROK_API_KEY 未配置${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Grok API密钥已配置${NC}"

# 检查私钥
GROK_PRIVATE_KEY=$(grep "^INDIVIDUAL_GROK_PRIVATE_KEY" .env | cut -d'=' -f2)
if [ -z "$GROK_PRIVATE_KEY" ] || [ "$GROK_PRIVATE_KEY" = "0xYOUR_KEY_HERE" ]; then
    echo -e "${RED}❌ 错误: INDIVIDUAL_GROK_PRIVATE_KEY 未配置${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Grok私钥已配置${NC}"

# 检查常规交易是否禁用
CONSENSUS_ENABLED=$(grep "^ENABLE_CONSENSUS_TRADING" .env | cut -d'=' -f2)
INDIVIDUAL_ENABLED=$(grep "^ENABLE_INDIVIDUAL_TRADING" .env | cut -d'=' -f2)
if [ "$CONSENSUS_ENABLED" = "False" ] && [ "$INDIVIDUAL_ENABLED" = "False" ]; then
    echo -e "${GREEN}✅ 常规交易已禁用（测试模式）${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 常规交易未禁用，可能影响测试结果${NC}"
fi

echo ""
echo "=========================================="
echo "🎯 配置总结"
echo "=========================================="
echo "测试AI: $NEWS_AIS"
echo "Grok模型: $(grep '^GROK_MODEL' .env | cut -d'=' -f2)"
echo "启用平台: $(grep '^ENABLED_PLATFORMS' .env | cut -d'=' -f2)"
echo "最小保证金: $(grep '^AI_MIN_MARGIN' .env | cut -d'=' -f2) USDT"
echo "最大杠杆: $(grep '^AI_MAX_LEVERAGE' .env | cut -d'=' -f2)x"
echo ""

# 询问是否继续
read -p "是否启动系统？[Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "=========================================="
echo "🚀 启动主系统"
echo "=========================================="
echo ""

# 启动主系统
python consensus_arena_multiplatform.py &
MAIN_PID=$!

echo "主系统PID: $MAIN_PID"
echo ""

# 等待系统启动
echo "等待系统初始化（5秒）..."
sleep 5

echo ""
echo "=========================================="
echo "📡 启动消息监听"
echo "=========================================="
echo ""

# 启动消息监听
RESPONSE=$(curl -s -X POST http://localhost:46000/api/news_trading/start)
echo "响应: $RESPONSE"

echo ""
echo "=========================================="
echo "✅ 系统已启动！"
echo "=========================================="
echo ""
echo "📊 监控面板: http://localhost:46000"
echo "📝 日志文件: tail -f logs/app.log"
echo ""
echo "🧪 测试命令:"
echo "  curl -X POST \"http://localhost:46000/api/news_trading/submit?url=xxx&coin=BTC\""
echo ""
echo "⏹️  停止系统:"
echo "  kill $MAIN_PID"
echo "  或 Ctrl+C"
echo ""
echo "=========================================="
echo ""

# 保持运行
wait $MAIN_PID

