#!/bin/bash

# SciPIP API 服务生产环境后台部署脚本
# 用法:
#   sh start_prod.sh start      - 后台启动API服务
#   sh start_prod.sh stop       - 停止API服务
#   sh start_prod.sh restart    - 重启API服务
#   sh start_prod.sh status     - 查看服务状态
#   sh start_prod.sh logs       - 查看服务日志
#   sh start_prod.sh help       - 显示帮助信息

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="/home/linweiquan/SciPIP"

# Conda 环境配置（如果使用 conda）
CONDA_ENV_NAME="scipip"
CONDA_BASE_PATH="/home/linweiquan/miniconda3"

# 进程管理
PID_DIR="$PROJECT_DIR/pids"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PID_DIR/api.pid"
LOG_FILE="$LOG_DIR/api.log"

# 查找 Python 可执行文件
find_python() {
    # 首先尝试 conda 环境中的 python
    if [ -d "$CONDA_BASE_PATH/envs/$CONDA_ENV_NAME" ]; then
        local conda_python="$CONDA_BASE_PATH/envs/$CONDA_ENV_NAME/bin/python"
        if [ -f "$conda_python" ]; then
            echo "$conda_python"
            return 0
        fi
    fi
    
    # 尝试系统 python3
    if command -v python3 &> /dev/null; then
        command -v python3
        return 0
    fi
    
    # 尝试 python
    if command -v python &> /dev/null; then
        command -v python
        return 0
    fi
    
    return 1
}

PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3"  # 默认值，会在后续检查中失败
fi

# 从配置文件读取端口（如果无法读取，使用默认值8888）
API_PORT=8888
if [ -f "$PROJECT_DIR/api_config.py" ] && [ -n "$PYTHON_CMD" ]; then
    API_PORT=$("$PYTHON_CMD" -c "import sys; sys.path.insert(0, '$PROJECT_DIR'); from api_config import API_PORT; print(API_PORT)" 2>/dev/null || echo "8888")
fi

# 创建必要的目录
mkdir -p "$PID_DIR" "$LOG_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    print_info "检查环境..."
    
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    # 检查必需文件
    required_files="$PROJECT_DIR/api_service.py $PROJECT_DIR/api_config.py $PROJECT_DIR/configs/datasets.yaml $PROJECT_DIR/scripts/env.sh"
    
    for file in $required_files; do
        if [ ! -f "$file" ] && [ ! -d "$file" ]; then
            print_warning "文件不存在: $file"
        fi
    done
    
    # 检查 Python 环境
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ] || [ ! -f "$PYTHON_CMD" ]; then
        print_error "未找到 Python，请先安装 Python 3 或激活 conda 环境"
        print_info "尝试的路径:"
        echo "  - $CONDA_BASE_PATH/envs/$CONDA_ENV_NAME/bin/python"
        echo "  - python3 (系统路径)"
        echo "  - python (系统路径)"
        exit 1
    fi
    
    print_info "使用 Python: $PYTHON_CMD"
    
    # 检查必要的 Python 包
    if ! "$PYTHON_CMD" -c "import fastapi" 2>/dev/null; then
        print_error "FastAPI 未安装，请先安装: pip install -r requirements_api.txt"
        print_info "或激活 conda 环境: conda activate $CONDA_ENV_NAME"
        exit 1
    fi
    
    print_success "环境检查通过"
}

# 检查服务是否运行
is_service_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 启动API服务（后台）
start_api_daemon() {
    print_info "启动 SciPIP API 服务（后台模式）..."
    
    # 检查服务是否已运行
    if is_service_running; then
        local pid=$(cat "$PID_FILE")
        print_warning "API服务已在运行中 (PID: $pid)"
        return 0
    fi
    
    # 检查端口是否被占用
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $API_PORT 已被占用，正在尝试停止现有服务..."
        # 尝试找到并停止占用端口的进程
        local port_pid=$(lsof -ti:$API_PORT)
        if [ -n "$port_pid" ]; then
            kill "$port_pid" 2>/dev/null || true
            sleep 2
        fi
    fi
    
    print_info "服务信息:"
    echo "  - API URL: http://localhost:$API_PORT"
    echo "  - 生成端点: POST http://localhost:$API_PORT/generate"
    echo "  - 健康检查: http://localhost:$API_PORT/health"
    echo "  - API文档: http://localhost:$API_PORT/docs"
    echo ""
    
    # 切换到项目目录
    cd "$PROJECT_DIR"
    
    # 获取 Python 命令
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ]; then
        print_error "无法找到 Python 可执行文件"
        exit 1
    fi
    
    # 后台启动API服务
    print_info "正在启动服务..."
    print_info "使用 Python: $PYTHON_CMD"
    nohup "$PYTHON_CMD" api_service.py > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 5
    
    # 检查服务是否成功启动
    if is_service_running; then
        # 再次检查进程是否真的在运行
        if ps -p "$pid" > /dev/null 2>&1; then
            print_success "API服务已启动，PID: $pid"
            print_info "日志文件: $LOG_FILE"
            print_info "访问地址: http://localhost:$API_PORT"
            print_info "查看日志: tail -f $LOG_FILE"
        else
            print_error "API服务启动失败，请查看日志: $LOG_FILE"
            rm -f "$PID_FILE"
            exit 1
        fi
    else
        print_error "API服务启动失败，请查看日志: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止服务
stop_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_info "停止 API 服务 (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 3
            
            # 强制杀死如果还在运行
            if ps -p "$pid" > /dev/null 2>&1; then
                print_warning "强制停止 API 服务..."
                kill -9 "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            rm -f "$PID_FILE"
            print_success "API服务已停止"
        else
            print_warning "API服务未运行"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "API服务未运行（PID文件不存在）"
    fi
    
    # 额外检查：如果端口仍被占用，尝试停止占用端口的进程
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $API_PORT 仍被占用，尝试停止占用该端口的进程..."
        local port_pid=$(lsof -ti:$API_PORT)
        if [ -n "$port_pid" ]; then
            kill "$port_pid" 2>/dev/null || true
            sleep 2
            if ps -p "$port_pid" > /dev/null 2>&1; then
                kill -9 "$port_pid" 2>/dev/null || true
            fi
        fi
    fi
}

# 重启服务
restart_service() {
    print_info "重启 API 服务..."
    stop_service
    sleep 2
    start_api_daemon
}

# 查看服务状态
show_status() {
    print_info "服务状态:"
    echo ""
    
    if is_service_running; then
        local pid=$(cat "$PID_FILE")
        print_success "API服务: 运行中 (PID: $pid)"
        
        # 显示进程信息
        if command -v ps &> /dev/null; then
            echo ""
            echo "进程信息:"
            ps -p "$pid" -o pid,ppid,cmd,etime,pmem,%cpu 2>/dev/null || true
        fi
    else
        print_warning "API服务: 未运行"
    fi
    
    echo ""
    print_info "端口占用情况:"
    local port_status=$(lsof -Pi :$API_PORT -sTCP:LISTEN -t 2>/dev/null)
    if [ -n "$port_status" ]; then
        echo "  $API_PORT: 被占用 (PID: $port_status)"
    else
        echo "  $API_PORT: 未占用"
    fi
    
    echo ""
    print_info "文件位置:"
    echo "  - PID文件: $PID_FILE"
    echo "  - 日志文件: $LOG_FILE"
}

# 查看服务日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "显示 API 服务日志 (最后50行):"
        echo ""
        tail -50 "$LOG_FILE"
        echo ""
        print_info "实时日志命令: tail -f $LOG_FILE"
    else
        print_error "日志文件不存在: $LOG_FILE"
    fi
}

# 显示帮助信息
show_help() {
    echo "SciPIP API 服务生产环境后台部署脚本"
    echo ""
    echo "用法:"
    echo "  sh start_prod.sh start      - 后台启动API服务"
    echo "  sh start_prod.sh stop       - 停止API服务"
    echo "  sh start_prod.sh restart    - 重启API服务"
    echo "  sh start_prod.sh status     - 查看服务状态"
    echo "  sh start_prod.sh logs       - 查看服务日志"
    echo "  sh start_prod.sh help       - 显示此帮助信息"
    echo ""
    echo "说明:"
    echo "  - 服务在后台运行，SSH断连不会影响服务"
    echo "  - 默认端口: $API_PORT (可在 api_config.py 或环境变量 SCIPIP_API_PORT 中配置)"
    echo "  - PID文件: $PID_FILE"
    echo "  - 日志文件: $LOG_FILE"
    echo ""
    echo "环境要求:"
    echo "  - Python 3.8+"
    echo "  - FastAPI, Uvicorn 等依赖（通过 requirements_api.txt 安装）"
    echo "  - Neo4j 数据库运行中"
    echo "  - 环境变量配置（通过 scripts/env.sh 设置）"
    echo ""
    echo "示例:"
    echo "  # 启动服务"
    echo "  sh start_prod.sh start"
    echo ""
    echo "  # 查看状态"
    echo "  sh start_prod.sh status"
    echo ""
    echo "  # 查看日志"
    echo "  sh start_prod.sh logs"
    echo ""
    echo "  # 停止服务"
    echo "  sh start_prod.sh stop"
    echo ""
    echo "  # 重启服务"
    echo "  sh start_prod.sh restart"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "🔬 SciPIP API 服务生产环境部署脚本"
    echo "=========================================="
    echo ""
    
    # 检查参数
    if [ $# -eq 0 ]; then
        print_error "缺少参数"
        show_help
        exit 1
    fi
    
    case "$1" in
        "start")
            check_environment
            start_api_daemon
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            check_environment
            restart_service
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
}

# 捕获中断信号
trap 'print_info "脚本已停止"; exit 0' INT TERM

# 运行主函数
main "$@"

