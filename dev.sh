#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  sql-agent-kit  开发模式启动脚本
#  前端: Vite dev server (localhost:5173, 热更新)
#  后端: uvicorn --reload (localhost:8000)
# ─────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    error "未找到 .venv，请先运行 ./start.sh 完成初始化"
fi
source .venv/bin/activate

# 检查 .env
[ ! -f ".env" ] && error ".env 不存在，请先运行 ./start.sh"

# 安装/更新依赖（快速检查）
info "检查 Python 依赖..."
python -m pip install --progress-bar on -r requirements-backend.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

info "检查前端依赖..."
cd frontend
[ ! -d "node_modules" ] && npm install --silent
cd ..

mkdir -p logs data config

# 清理退出时杀掉整个进程组（含 uvicorn --reload 产生的 worker 子进程）
cleanup() {
    echo ""
    info "正在停止服务..."
    # 杀掉以当前脚本为 leader 的整个进程组
    kill -- -$$ 2>/dev/null || true
    ok "已停止"
}
trap cleanup EXIT INT TERM

# 启动后端
info "启动后端 → http://localhost:8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 启动前端
info "启动前端 → http://localhost:5173"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  前端（热更新）: http://localhost:5173${NC}"
echo -e "${GREEN}  后端（API）:    http://localhost:8000${NC}"
echo -e "${GREEN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 等待任意子进程退出
wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || wait
