#!/bin/bash
# 一键启动：启动服务 + 执行词根校验流水线
# 用法: bash start.sh [root_word_ids]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PORT=8000
API="http://localhost:${PORT}/api/v1"

echo "========================================"
echo "  词根校验流水线 - 一键启动"
echo "========================================"

# 1. 清理旧进程和缓存
echo "[1/4] 清理旧进程和缓存..."
netstat -ano 2>/dev/null | grep ":${PORT}" | grep LISTENING | awk '{print $NF}' | while read pid; do
    taskkill //F //PID "$pid" 2>/dev/null && echo "  已停止 PID=$pid"
done
find "$SCRIPT_DIR/app" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$SCRIPT_DIR/app" -name "*.pyc" -delete 2>/dev/null
echo "  完成"

# 2. 启动服务
echo "[2/4] 启动 FastAPI 服务..."
nohup uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT} > /tmp/uvicorn.log 2>&1 &
SERVER_PID=$!

# 等待服务就绪
for i in $(seq 1 30); do
    if curl -s "${API}/health" > /dev/null 2>&1; then
        echo "  服务已就绪 (PID=$SERVER_PID)"
        break
    fi
    sleep 1
done

if ! curl -s "${API}/health" > /dev/null 2>&1; then
    echo "  错误: 服务启动超时"
    exit 1
fi

# 3. 执行流水线
echo "[3/4] 执行词根校验..."

if [ -n "$1" ]; then
    RESULT=$(curl -s -X POST "${API}/root-word/process?root_word_ids=$1" -H "Content-Type: application/json")
else
    RESULT=$(curl -s -X POST "${API}/root-word/process?limit=100" -H "Content-Type: application/json")
fi

# 4. 输出结果
echo "[4/4] 结果:"
echo "$RESULT" | python -m json.tool 2>/dev/null || echo "$RESULT"

# 汇总
TOTAL=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['total'])" 2>/dev/null || echo "?")
MATCHED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['matched'])" 2>/dev/null || echo "?")
UNMATCHED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['unmatched'])" 2>/dev/null || echo "?")

echo ""
echo "========================================"
echo "  完成: 共 ${TOTAL} 条, 命中 ${MATCHED}, 未命中 ${UNMATCHED}"
echo "  服务运行中: http://localhost:${PORT}"
echo "  日志: /tmp/uvicorn.log"
echo "========================================"
