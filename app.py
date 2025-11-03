import sys
import os

sys.path.append("./src")

# 自动加载环境变量
def load_env_file(env_file=None):
    """从 env.sh 文件加载环境变量"""
    if env_file is None:
        # 获取 app.py 所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(script_dir, "scripts", "env.sh")
    
    if os.path.exists(env_file):
        try:
            # 读取 env.sh 文件
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if line and not line.startswith('#') and 'export' in line:
                        # 解析 export KEY="VALUE" 格式
                        line = line.replace('export ', '')
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # 只设置未设置的环境变量
                            if key not in os.environ:
                                os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load environment variables from {env_file}: {e}")

# 在导入其他模块之前加载环境变量
load_env_file()

import streamlit as st
from app_pages import (
    button_interface,
    step_by_step_generation,
    one_click_generation,
    homepage,
)
from app_pages.locale import _

if __name__ == "__main__":
    backend = button_interface.Backend()
    # backend = None
    st.set_page_config(layout="wide")

    # st.logo("./assets/pic/logo.jpg", size="large")
    def fn1():
        one_click_generation.one_click_generation(backend)

    def fn2():
        step_by_step_generation.step_by_step_generation(backend)

    pg = st.navigation([
        st.Page(homepage.home_page, title=_("🏠️ Homepage")),
        st.Page(fn1, title=_("💧 One-click Generation")),
        st.Page(fn2, title=_("💦 Step-by-step Generation")),
    ])
    pg.run()