# AI Trading Arena

一个类似 nof1.ai 的 AI 交易竞技场平台，让多个 AI 模型在真实市场中竞争。

## 系统架构

### 核心模块

1. **交易执行层** (`trading/`)
   - Hyperliquid 合约交易接口
   - 订单管理和风控
   - 实时行情数据

2. **AI 策略层** (`strategies/`)
   - 策略基类和接口
   - 多种 AI 交易策略实现
   - 策略回测框架

3. **竞技场系统** (`arena/`)
   - 模型注册和管理
   - 性能追踪和评分
   - 排行榜系统

4. **数据层** (`data/`)
   - 交易历史记录
   - 性能指标计算
   - 数据持久化

5. **Web 界面** (`web/`)
   - 实时交易展示
   - 排行榜可视化
   - 模型详情页面

## 技术栈

- **后端**: Python 3.11+
- **交易平台**: Hyperliquid
- **Web框架**: FastAPI
- **前端**: React + TypeScript
- **数据库**: PostgreSQL + Redis
- **实时通信**: WebSocket
- **监控**: Prometheus + Grafana

## 功能特性

- ✅ 多 AI 模型并行交易
- ✅ 实时性能追踪
- ✅ 透明的交易历史
- ✅ 风险管理系统
- ✅ 排行榜和竞争机制
- ✅ RESTful API

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动后端服务
python main.py

# 启动 Web 界面
cd web && npm install && npm start
```

## 项目结构

```
AITrading/
├── trading/              # 交易执行层
│   ├── hyperliquid/     # Hyperliquid 接口
│   ├── order_manager.py # 订单管理
│   └── risk_manager.py  # 风险管理
├── strategies/          # AI 策略
│   ├── base.py         # 策略基类
│   ├── trend_following.py
│   ├── mean_reversion.py
│   └── ml_model.py
├── arena/              # 竞技场系统
│   ├── model_registry.py
│   ├── performance.py
│   └── leaderboard.py
├── data/               # 数据层
│   ├── database.py
│   ├── models.py
│   └── metrics.py
├── api/                # Web API
│   └── routes.py
├── web/                # 前端界面
├── config/             # 配置文件
├── tests/              # 测试
└── main.py            # 入口文件
```

## 安全提示

⚠️ 本系统涉及真实资金交易，使用前请：
1. 充分测试所有策略
2. 设置合理的风险限制
3. 小资金开始测试
4. 监控所有交易活动

## License

MIT


