# 多平台对比交易指南

## 概述

本系统支持同时在多个交易平台（Hyperliquid 和 Aster）上执行相同的 AI 交易决策，并实时对比各平台的收益表现。

## 功能特性

✅ **统一决策，多平台执行**：AI 做出的每个交易决策会同时在所有启用的平台上执行
✅ **实时收益对比**：实时追踪和对比各平台的盈亏、ROI、胜率等指标  
✅ **独立持仓管理**：每个平台的持仓独立管理，互不影响
✅ **灵活配置**：可以选择启用单个或多个平台
✅ **统一接口**：基于抽象基类设计，易于扩展新平台

## 架构说明

### 核心组件

1. **BaseExchangeClient** (`trading/base_client.py`)
   - 定义统一的交易所客户端接口
   - 所有平台客户端必须实现此接口

2. **HyperliquidClient** (`trading/hyperliquid/client.py`)
   - Hyperliquid 平台客户端实现
   - 使用官方 Python SDK

3. **AsterClient** (`trading/aster/client.py`)
   - Aster 平台客户端实现
   - 基于 REST API 封装
   - ⚠️ **注意**：需要根据 Aster 实际 API 文档调整 API 端点和数据格式

4. **MultiPlatformTrader** (`trading/multi_platform_trader.py`)
   - 多平台交易管理器
   - 负责协调多个平台的交易执行
   - 提供统一的统计和对比功能

5. **ConsensusArena（多平台版）** (`consensus_arena_multiplatform.py`)
   - 支持多平台对比的共识竞技场
   - 每个 AI 组在所有平台上同时交易
   - 实时对比各平台表现

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例配置文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键参数：

```bash
# 启用的平台（可选：hyperliquid, aster）
ENABLED_PLATFORMS=hyperliquid,aster

# Hyperliquid 配置
GROUP_1_PRIVATE_KEY=0x...  # Alpha 组私钥
GROUP_2_PRIVATE_KEY=0x...  # Beta 组私钥

# Aster 配置
ASTER_TESTNET=True
ASTER_API_URL=https://testnet-api.aster.exchange  # 根据实际修改

# AI API Keys
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
# ... 其他 AI API Keys
```

### 3. 运行多平台版本

```bash
python consensus_arena_multiplatform.py
```

或者使用原版（仅 Hyperliquid）：
```bash
python consensus_arena.py
```

### 4. 访问 Web 界面

打开浏览器访问：
```
http://localhost:46000
```

## API 端点

### 获取系统状态
```
GET /api/status
```

返回：
- 各组在各平台的余额、盈亏、ROI
- 共识决策历史
- 持仓信息

### 获取平台对比数据
```
GET /api/platform_comparison
```

返回：
- 各平台详细对比统计
- 最佳/最差平台
- 平均 ROI

## 配置说明

### 平台选择

通过 `ENABLED_PLATFORMS` 环境变量控制启用哪些平台：

```bash
# 仅 Hyperliquid
ENABLED_PLATFORMS=hyperliquid

# 仅 Aster
ENABLED_PLATFORMS=aster

# 同时启用两个平台
ENABLED_PLATFORMS=hyperliquid,aster
```

### 多平台模式开关

```bash
# 启用多平台对比模式
MULTI_PLATFORM_MODE=True

# 在日志中显示平台对比
PLATFORM_COMPARISON_ENABLED=True
```

## Aster 集成注意事项

⚠️ **重要**：当前 Aster 客户端实现是基于常见交易所 API 模式的模板，需要根据 Aster 实际 API 文档进行调整：

1. **API 端点**：修改 `AsterClient` 中的所有 API 端点路径
2. **请求格式**：调整请求参数的格式和命名
3. **响应解析**：根据实际响应格式修改数据提取逻辑
4. **签名算法**：确认并实现正确的请求签名方法

### 需要修改的关键位置

```python
# trading/aster/client.py

# 1. 修改 API 基础 URL
self.base_url = "https://实际的aster-api地址.com"

# 2. 调整各个方法的 API 端点
# 例如：
async def get_market_data(self, coin: str) -> Dict:
    result = await self._request("GET", "/实际的端点路径/{coin}")
    # 根据实际响应格式提取数据
    return {...}

# 3. 修改签名算法（如果需要）
def _create_signature(self, message: str) -> str:
    # 实现 Aster 要求的签名算法
    pass
```

## 收益对比功能

### 实时对比指标

系统会实时追踪和对比以下指标：

- **余额**：当前账户总值
- **盈亏**：相对于初始余额的绝对盈亏
- **ROI**：投资回报率（百分比）
- **交易次数**：已执行的交易笔数
- **胜率**：盈利交易占比

### 查看对比数据

#### 方法 1：查看日志

系统会在每个决策周期后打印平台对比：

```
[Alpha组] 📊 平台收益对比:
  Alpha组-Hyperliquid: 余额=$1050.00, 盈亏=$+50.00, ROI=+5.00%, 胜率=60.0%
  Alpha组-Aster: 余额=$1080.00, 盈亏=$+80.00, ROI=+8.00%, 胜率=65.0%
```

#### 方法 2：API 接口

```bash
# 获取详细对比数据
curl http://localhost:46000/api/platform_comparison
```

#### 方法 3：Web 界面

在 Web 界面中可以查看：
- 各平台权益曲线对比
- 详细交易记录
- 实时统计指标

## 扩展新平台

如果需要接入其他交易平台：

1. 创建新的客户端类，继承 `BaseExchangeClient`
2. 实现所有抽象方法
3. 在配置中添加平台相关配置
4. 在 `AIGroup.__init__` 中添加平台初始化逻辑

示例：

```python
# trading/newplatform/client.py
from trading.base_client import BaseExchangeClient

class NewPlatformClient(BaseExchangeClient):
    @property
    def platform_name(self) -> str:
        return "NewPlatform"
    
    # 实现所有抽象方法...
```

## 风险提示

⚠️ **重要提示**：

1. **测试网优先**：建议先在测试网上充分测试
2. **资金隔离**：每个平台使用独立的私钥和账户
3. **API 限制**：注意各平台的 API 请求频率限制
4. **网络问题**：某个平台网络故障不影响其他平台
5. **费率差异**：不同平台的手续费可能影响收益对比

## 常见问题

### Q: 为什么某个平台没有执行交易？

A: 检查以下几点：
1. 该平台是否在 `ENABLED_PLATFORMS` 中启用
2. 私钥配置是否正确
3. 账户余额是否充足
4. 查看日志中的错误信息

### Q: 如何只在单个平台上测试？

A: 设置 `ENABLED_PLATFORMS=hyperliquid` 或 `ENABLED_PLATFORMS=aster`

### Q: 各平台的交易会互相影响吗？

A: 不会。每个平台的持仓和资金完全独立管理。

### Q: Aster 客户端无法连接？

A: 需要根据 Aster 实际 API 文档修改客户端实现，特别是：
- API URL
- 端点路径
- 签名算法
- 数据格式

## 贡献

如果你成功接入了 Aster 或其他平台，欢迎提交 PR 分享你的实现！

## 支持

如有问题，请查看日志或提 Issue。

