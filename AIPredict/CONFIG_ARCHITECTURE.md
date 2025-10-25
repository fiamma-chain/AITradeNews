# 配置架构说明

## 📋 `.env` vs `settings.py` 分工

### 🎯 设计原理

```
.env 文件 (环境变量)
    ↓ Pydantic自动读取
settings.py (配置类 + 默认值)
    ↓ 导入使用
业务代码 (from config.settings import settings)
```

---

## ✅ 正确的职责划分

### **`.env` 的职责**
**存储敏感数据和用户自定义配置（不提交到Git）**

#### 应该包含：
- ✅ **API密钥**（私钥、token）
- ✅ **环境差异配置**（测试/生产切换）
- ✅ **用户自定义参数**（保证金、杠杆等）
- ✅ **覆盖默认值的配置**

#### 示例：
```bash
# 敏感数据（必需）
DEEPSEEK_API_KEY=sk-xxx
GROUP_1_PRIVATE_KEY=0xYOUR_KEY

# 用户自定义（可选，覆盖默认值）
AI_MIN_MARGIN=100.0      # 覆盖默认值
MIN_CONFIDENCE=50.0      # 覆盖默认值
```

---

### **`settings.py` 的职责**
**定义配置结构、类型、默认值和验证规则（提交到Git）**

#### 应该包含：
- ✅ **类型声明**（`str`, `float`, `bool`）
- ✅ **合理的默认值**（作为fallback）
- ✅ **验证逻辑**（如私钥格式检查）
- ✅ **辅助函数**（如`get_allowed_symbols()`）

#### 示例：
```python
class Settings(BaseSettings):
    # 类型 + 默认值
    ai_min_margin: float = 100.0  # 默认100U
    min_confidence: float = 60.0   # 默认60%
    
    # 敏感数据（默认空字符串，从.env读取）
    claude_api_key: str = ""
    
    class Config:
        env_file = ".env"  # 自动加载.env
```

---

## 🔄 配置加载优先级

```
1. .env 文件（最高优先级）
   ↓ 如果没有配置
2. settings.py 默认值
   ↓ 如果还是空
3. 运行时错误（敏感数据必需）
```

### 示例流程：

```python
# settings.py
ai_min_margin: float = 100.0

# .env
AI_MIN_MARGIN=120.0

# 业务代码
settings.ai_min_margin  # → 120.0（来自.env）
```

如果`.env`没配置：
```python
# settings.py
ai_min_margin: float = 100.0

# .env（没有AI_MIN_MARGIN）

# 业务代码
settings.ai_min_margin  # → 100.0（来自默认值）
```

---

## 📊 当前配置分类

### **必需配置（.env中必须填写）**
```bash
# API密钥
DEEPSEEK_API_KEY=
CLAUDE_API_KEY=
GROK_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
QWEN_API_KEY=

# 交易私钥
GROUP_1_PRIVATE_KEY=
GROUP_2_PRIVATE_KEY=
INDIVIDUAL_XXX_PRIVATE_KEY=  # 可选，不填则不启用独立交易
```

### **可选配置（有默认值，通常无需修改）**
```bash
# 交易参数（settings.py有合理默认值）
AI_MIN_MARGIN=100.0              # 默认100U
AI_MAX_MARGIN=240.0              # 默认240U
AI_MAX_LEVERAGE=5.0              # 默认5x
MIN_CONFIDENCE=60.0              # 默认60%
CONSENSUS_INTERVAL=300           # 默认5分钟

# 环境配置（默认主网）
HYPERLIQUID_TESTNET=False
ASTER_TESTNET=False
ENABLED_PLATFORMS=hyperliquid,aster

# API端口（默认46000）
API_PORT=46000
```

### **特殊用途配置（仅特定场景需要）**
```bash
# 性能测试模式
ENABLE_CONSENSUS_TRADING=False   # 禁用共识交易
ENABLE_INDIVIDUAL_TRADING=False  # 禁用独立AI交易
NEWS_TRADING_ENABLED=True        # 启用消息交易测试

# 国际化
QWEN_USE_INTERNATIONAL=true      # Qwen国际版API
```

---

## ⚠️ 常见问题

### **Q1: 为什么`.env`和`settings.py`都有`ai_min_margin`？**

**A**: 不冲突，这是设计：
- `settings.py`: 提供**默认值**（100.0）
- `.env`: 用户可以**覆盖**默认值

如果`.env`中不配置，就使用默认值。

---

### **Q2: 哪些配置应该放`.env`？**

**判断标准**：
1. 是敏感数据吗？ → `.env`
2. 需要在不同环境不同吗？ → `.env`
3. 用户需要自定义吗？ → `.env`（可选）
4. 其他 → 只在`settings.py`

---

### **Q3: `.env`可以删掉一些配置吗？**

**A**: 可以！删掉的配置会使用`settings.py`的默认值。

**推荐最小化`.env`配置**（只保留必需项）：
```bash
# 最小化.env（仅必需）
DEEPSEEK_API_KEY=xxx
CLAUDE_API_KEY=xxx
...
GROUP_1_PRIVATE_KEY=0xYOUR_KEY
GROUP_2_PRIVATE_KEY=0xYOUR_KEY
INDIVIDUAL_DEEPSEEK_PRIVATE_KEY=0xYOUR_KEY
...
```

---

## 🎯 最佳实践

### ✅ **推荐做法**

1. **`.env`只配置必需项和需要覆盖的项**
2. **`settings.py`提供合理的默认值**
3. **`.env.example`作为模板（包含说明）**
4. **`.env`不提交到Git**

### ❌ **不推荐做法**

1. ❌ `.env`中配置所有项（冗余）
2. ❌ `settings.py`没有默认值（不友好）
3. ❌ 把敏感数据写在`settings.py`（安全问题）

---

## 📝 配置文件角色总结

| 文件 | 角色 | 提交Git | 说明 |
|------|------|---------|------|
| `.env` | 用户配置 | ❌ 不提交 | 敏感数据、用户自定义 |
| `settings.py` | 配置结构 | ✅ 提交 | 类型、默认值、验证 |
| `env.example.txt` | 配置模板 | ✅ 提交 | 帮助用户填写`.env` |

---

## 🔧 如何简化当前配置

### **步骤1：精简`.env`**

删除所有有默认值且不需要修改的配置：
```bash
# 可以删除（使用默认值）
# AI_INITIAL_BALANCE=240.0        # 默认240
# CONSENSUS_MIN_VOTES=2            # 默认2
# HYPERLIQUID_TESTNET=False        # 默认主网
```

### **步骤2：只保留必需和自定义项**
```bash
# 保留：API密钥（必需）
DEEPSEEK_API_KEY=xxx

# 保留：私钥（必需）
GROUP_1_PRIVATE_KEY=0xYOUR_KEY

# 保留：用户自定义（覆盖默认值）
AI_MIN_MARGIN=100.0  # 如果默认值不合适
```

---

## ✅ 总结

| 特性 | `.env` | `settings.py` |
|------|--------|---------------|
| **职责** | 存储敏感数据和用户配置 | 定义配置结构和默认值 |
| **内容** | 实际的值 | 类型+默认值+验证 |
| **提交Git** | ❌ 不提交 | ✅ 提交 |
| **优先级** | 高（覆盖默认值） | 低（fallback） |
| **最佳实践** | 最小化配置 | 完整的配置定义 |

---

**核心原则**：`.env`是用户的，`settings.py`是开发者的。

