.PHONY: help install setup run dev clean test lint status ps port logs logs-list logs-clean

# 默认目标
.DEFAULT_GOAL := help

# 项目配置
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
PROJECT_DIR := $(shell pwd)

# 颜色输出
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  AI Trading Arena - 启动命令$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)快速开始:$(NC)"
	@echo "  1. make install    # 安装依赖"
	@echo "  2. make setup      # 配置环境变量"
	@echo "  3. make run        # 运行项目"
	@echo ""

install: ## 安装Python依赖包
	@echo "$(BLUE)📦 安装依赖包...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)⚠️  虚拟环境不存在，正在创建...$(NC)"; \
		python3 -m venv $(VENV); \
	fi
	@echo "$(GREEN)✓ 虚拟环境就绪$(NC)"
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ 依赖安装完成！$(NC)"

setup: ## 设置环境变量（从env.example.txt创建.env）
	@echo "$(BLUE)⚙️  配置环境变量...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f env.example.txt ]; then \
			cp env.example.txt .env; \
			echo "$(GREEN)✓ 已创建 .env 文件$(NC)"; \
			echo "$(YELLOW)⚠️  请编辑 .env 文件，填入你的 API Keys 和私钥！$(NC)"; \
			echo "$(YELLOW)   必填项：$(NC)"; \
			echo "   - CLAUDE_API_KEY"; \
			echo "   - OPENAI_API_KEY"; \
			echo "   - GEMINI_API_KEY"; \
			echo "   - QWEN_API_KEY"; \
			echo "   - GROK_API_KEY"; \
			echo "   - DEEPSEEK_API_KEY"; \
			echo "   - GROUP_1_PRIVATE_KEY (Alpha组)"; \
			echo "   - GROUP_2_PRIVATE_KEY (Beta组)"; \
		else \
			echo "$(RED)❌ env.example.txt 文件不存在$(NC)"; \
			exit 1; \
		fi \
	else \
		echo "$(GREEN)✓ .env 文件已存在$(NC)"; \
	fi

run: ## 运行AI交易系统（后台模式）
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🚀 启动 AI Trading Arena$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(YELLOW)⚠️  服务已在运行！$(NC)"; \
		echo "$(YELLOW)   查看日志: make logs$(NC)"; \
		echo "$(YELLOW)   停止服务: make stop$(NC)"; \
		exit 1; \
	fi
	@mkdir -p logs
	@LOG_FILE="logs/server-$$(date +%Y-%m-%d-%H).log"; \
	echo "$(GREEN)✓ 启动服务...$(NC)"; \
	echo "$(YELLOW)📌 Web界面地址: http://localhost:46000$(NC)"; \
	echo "$(YELLOW)📌 日志文件: $$LOG_FILE$(NC)"; \
	echo "$(YELLOW)📌 查看日志: make logs$(NC)"; \
	echo "$(YELLOW)📌 停止服务: make stop$(NC)"; \
	cd $(PROJECT_DIR) && nohup $(PYTHON) consensus_arena_multiplatform.py >> $$LOG_FILE 2>&1 & \
	echo $$! > logs/server.pid; \
	sleep 2; \
	if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(GREEN)✓ 服务启动成功！$(NC)"; \
	else \
		echo "$(RED)❌ 服务启动失败，请查看日志$(NC)"; \
		exit 1; \
	fi

dev: ## 运行AI交易系统（开发模式，显示详细日志）
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  🔧 启动 AI Trading Arena (开发模式)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@export LOG_LEVEL=DEBUG && cd $(PROJECT_DIR) && $(PYTHON) consensus_arena_multiplatform.py

clean: ## 清理临时文件和缓存（不删除logs）
	@echo "$(BLUE)🧹 清理临时文件...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "nohup.out" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ 清理完成（日志文件已保留）$(NC)"
	@echo "$(YELLOW)提示: 使用 'make logs-clean' 清理旧日志$(NC)"

test: ## 运行测试（如果有）
	@echo "$(BLUE)🧪 运行测试...$(NC)"
	@if [ -d "tests" ]; then \
		$(PYTHON) -m pytest tests/; \
	else \
		echo "$(YELLOW)⚠️  未找到测试目录$(NC)"; \
	fi

lint: ## 代码格式检查
	@echo "$(BLUE)🔍 检查代码格式...$(NC)"
	@$(PIP) list | grep -q flake8 || $(PIP) install flake8
	@$(PYTHON) -m flake8 . --exclude=venv,.venv,__pycache__ --max-line-length=120 || echo "$(YELLOW)⚠️  发现代码格式问题$(NC)"

status: ## 显示系统状态
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  📊 系统状态$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)服务状态:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		echo "  $(GREEN)✓ 运行中 (PID: $$PID)$(NC)"; \
		if [ -f "logs/server.pid" ]; then \
			SAVED_PID=$$(cat logs/server.pid); \
			echo "  $(GREEN)✓ PID文件: $$SAVED_PID$(NC)"; \
		fi; \
	else \
		echo "  $(RED)❌ 未运行$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)Python:$(NC)"
	@$(PYTHON) --version 2>/dev/null || echo "  $(RED)❌ 虚拟环境未激活$(NC)"
	@echo ""
	@echo "$(GREEN)虚拟环境:$(NC)"
	@if [ -d "$(VENV)" ]; then echo "  $(GREEN)✓ 已创建$(NC)"; else echo "  $(RED)❌ 未创建$(NC)"; fi
	@echo ""
	@echo "$(GREEN)配置文件:$(NC)"
	@if [ -f ".env" ]; then echo "  $(GREEN)✓ .env 存在$(NC)"; else echo "  $(RED)❌ .env 不存在$(NC)"; fi
	@echo ""
	@echo "$(GREEN)依赖包:$(NC)"
	@$(PIP) list 2>/dev/null | wc -l | xargs -I {} echo "  已安装 {} 个包"
	@echo ""
	@echo "$(GREEN)日志文件:$(NC)"
	@if [ -d "logs" ]; then \
		COUNT=$$(ls logs/server-*.log 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$COUNT" -gt 0 ]; then \
			echo "  $(GREEN)✓ $$COUNT 个日志文件$(NC)"; \
			LATEST=$$(ls -t logs/server-*.log 2>/dev/null | head -1); \
			if [ -n "$$LATEST" ]; then \
				SIZE=$$(ls -lh "$$LATEST" | awk '{print $$5}'); \
				echo "  最新: $$LATEST ($$SIZE)"; \
			fi; \
		else \
			echo "  $(YELLOW)⚠️  无日志文件$(NC)"; \
		fi; \
	else \
		echo "  $(YELLOW)⚠️  logs 目录不存在$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)服务端口:$(NC)"
	@if [ -f .env ]; then \
		PORT=$$(grep "^API_PORT=" .env | cut -d'=' -f2 | tr -d ' '); \
		if [ -n "$$PORT" ]; then \
			echo "  $(GREEN)✓ $$PORT$(NC) (配置)"; \
			echo "  $(GREEN)✓ http://localhost:$$PORT$(NC)"; \
		else \
			echo "  $(GREEN)✓ 46000$(NC) (默认)"; \
			echo "  $(GREEN)✓ http://localhost:46000$(NC)"; \
		fi; \
	else \
		echo "  $(GREEN)✓ 46000$(NC) (默认)"; \
	fi
	@echo "  查看详情: make port"

ps: ## 显示服务进程信息
	@echo "$(BLUE)🔍 进程信息:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		echo "$(GREEN)✓ 服务运行中$(NC)"; \
		echo ""; \
		ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{printf "  PID: %s\n  CPU: %s%%\n  MEM: %s%%\n  启动时间: %s %s\n  命令: %s\n", $$2, $$3, $$4, $$9, $$10, $$11}'; \
	else \
		echo "$(RED)❌ 服务未运行$(NC)"; \
	fi

port: ## 查看服务端口信息
	@echo "$(BLUE)🌐 服务端口信息:$(NC)"
	@echo ""
	@echo "$(GREEN)配置端口:$(NC)"
	@if [ -f .env ]; then \
		PORT=$$(grep "^API_PORT=" .env | cut -d'=' -f2 | tr -d ' '); \
		if [ -n "$$PORT" ]; then \
			echo "  端口: $$PORT"; \
			echo "  地址: http://localhost:$$PORT"; \
		else \
			echo "  端口: 46000 (默认)"; \
			echo "  地址: http://localhost:46000"; \
		fi; \
	else \
		echo "  端口: 46000 (默认)"; \
		echo "  地址: http://localhost:46000"; \
	fi
	@echo ""
	@echo "$(GREEN)实际监听端口:$(NC)"
	@if ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" > /dev/null; then \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		if command -v lsof > /dev/null 2>&1; then \
			PORTS=$$(lsof -Pan -p $$PID -i 2>/dev/null | grep LISTEN | awk '{print $$9}' | cut -d':' -f2 | sort -u); \
			if [ -n "$$PORTS" ]; then \
				echo "  $(GREEN)✓ 服务正在监听以下端口:$(NC)"; \
				for port in $$PORTS; do \
					echo "    - $$port"; \
				done; \
			else \
				echo "  $(YELLOW)⚠️  未检测到监听端口（服务可能正在启动中）$(NC)"; \
			fi; \
		elif command -v netstat > /dev/null 2>&1; then \
			PORTS=$$(netstat -tuln 2>/dev/null | grep LISTEN | grep ":88" | awk '{print $$4}' | cut -d':' -f2 | sort -u); \
			if [ -n "$$PORTS" ]; then \
				echo "  $(GREEN)✓ 服务正在监听以下端口:$(NC)"; \
				for port in $$PORTS; do \
					echo "    - $$port"; \
				done; \
			else \
				echo "  $(YELLOW)⚠️  未检测到监听端口$(NC)"; \
			fi; \
		else \
			echo "  $(YELLOW)⚠️  无法检测端口（需要 lsof 或 netstat 命令）$(NC)"; \
		fi; \
	else \
		echo "  $(RED)❌ 服务未运行$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)提示:$(NC)"
	@echo "  - 检查所有监听端口: lsof -i -P | grep LISTEN"
	@echo "  - 检查特定端口: lsof -i :46000"
	@echo "  - 测试端口连接: curl http://localhost:46000/api/status"

reinstall: clean ## 重新安装所有依赖
	@echo "$(BLUE)🔄 重新安装依赖...$(NC)"
	@rm -rf $(VENV)
	@$(MAKE) install

update: ## 更新依赖包
	@echo "$(BLUE)⬆️  更新依赖包...$(NC)"
	@$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ 更新完成$(NC)"

# 快捷命令
start: run ## run 的别名

stop: ## 停止所有服务
	@echo "$(BLUE)🛑 停止服务...$(NC)"
	@if [ -f logs/server.pid ]; then \
		PID=$$(cat logs/server.pid); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "$(GREEN)✓ 服务已停止 (PID: $$PID)$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  PID文件存在但进程不存在$(NC)"; \
		fi; \
		rm -f logs/server.pid; \
	else \
		PID=$$(ps aux | grep -v grep | grep -v make | grep "[p]ython.*consensus_arena_multiplatform.py" | awk '{print $$2}' | head -1); \
		if [ -n "$$PID" ]; then \
			kill $$PID 2>/dev/null && \
				echo "$(GREEN)✓ 服务已停止 (PID: $$PID)$(NC)" || \
				echo "$(RED)❌ 停止失败$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  服务未运行$(NC)"; \
		fi; \
	fi

restart: ## 重启服务
	@$(MAKE) stop || true
	@sleep 1
	@$(MAKE) run

logs: ## 实时查看日志
	@echo "$(BLUE)📜 实时查看日志...$(NC)"
	@if [ -d "logs" ] && [ -n "$$(ls -t logs/server-*.log 2>/dev/null | head -1)" ]; then \
		LATEST_LOG=$$(ls -t logs/server-*.log | head -1); \
		echo "$(GREEN)日志文件: $$LATEST_LOG$(NC)"; \
		echo "$(YELLOW)按 Ctrl+C 退出$(NC)"; \
		echo ""; \
		tail -f $$LATEST_LOG; \
	else \
		echo "$(YELLOW)⚠️  未找到日志文件$(NC)"; \
		echo "$(YELLOW)   请先启动服务: make run$(NC)"; \
	fi

logs-list: ## 列出所有日志文件
	@echo "$(BLUE)📂 日志文件列表:$(NC)"
	@if [ -d "logs" ]; then \
		ls -lh logs/server-*.log 2>/dev/null | awk '{print "  " $$9 " (" $$5 ")"}' || \
		echo "$(YELLOW)  未找到日志文件$(NC)"; \
	else \
		echo "$(YELLOW)  logs 目录不存在$(NC)"; \
	fi

logs-clean: ## 清理旧日志（保留最近7天）
	@echo "$(BLUE)🧹 清理旧日志...$(NC)"
	@if [ -d "logs" ]; then \
		find logs -name "server-*.log" -type f -mtime +7 -delete 2>/dev/null; \
		echo "$(GREEN)✓ 已删除7天前的日志文件$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  logs 目录不存在$(NC)"; \
	fi

check-api-keys: ## 检查API Keys是否配置
	@echo "$(BLUE)🔑 检查 API Keys 配置...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env 文件不存在$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)正在检查配置...$(NC)"
	@grep "CLAUDE_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Claude$(NC)" || echo "  $(RED)❌ Claude$(NC)"
	@grep "OPENAI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ OpenAI$(NC)" || echo "  $(RED)❌ OpenAI$(NC)"
	@grep "GEMINI_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Gemini$(NC)" || echo "  $(RED)❌ Gemini$(NC)"
	@grep "QWEN_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Qwen$(NC)" || echo "  $(RED)❌ Qwen$(NC)"
	@grep "GROK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Grok$(NC)" || echo "  $(RED)❌ Grok$(NC)"
	@grep "DEEPSEEK_API_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ DeepSeek$(NC)" || echo "  $(RED)❌ DeepSeek$(NC)"
	@grep "GROUP_1_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Alpha组私钥$(NC)" || echo "  $(RED)❌ Alpha组私钥$(NC)"
	@grep "GROUP_2_PRIVATE_KEY" .env | grep -v "your_" > /dev/null && echo "  $(GREEN)✓ Beta组私钥$(NC)" || echo "  $(RED)❌ Beta组私钥$(NC)"

quick-start: install setup ## 一键完整安装和启动
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  ✅ 安装完成！$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📝 下一步：$(NC)"
	@echo "  1. 编辑 .env 文件，填入你的 API Keys 和私钥"
	@echo "  2. 运行: make check-api-keys 检查配置"
	@echo "  3. 运行: make run 启动系统"
	@echo ""

