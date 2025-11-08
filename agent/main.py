import sys
import logging
import os
from datetime import datetime
from pathlib import Path
import locale
import codecs

# 确保当前脚本所在目录在 Python 路径中
script_dir = Path(__file__).parent.absolute()
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 设置 GBK 编码（在所有导入之前）
# set_utf8_encoding()
    
print(f"脚本目录: {script_dir}")
print(f"工作目录: {os.getcwd()}")
print(f"Python 路径: {sys.path[:3]}")  # 只打印前3个

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

# 全局配置变量
GAME_CONFIG = {
    # "dodge_key": win32con.VK_RBUTTON  # 默认闪避键为 右键 (0x02)
    "dodge_key": 160,  # 左 Shift 键 (0xA0)
    "auto_battle_mode": 0,  # 自动战斗模式：0=循环按E键, 1=什么也不做
    "battle_rounds": 3  # 战斗轮数
}

# 重要：必须在 AgentServer.start_up() 之前导入，以便装饰器注册自定义 Action 和 Recognition
import my_action
import my_reco
import common
import setting
import tools


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """请求管理员权限重新运行当前脚本"""
    try:
        import ctypes
        # 避免修改编码
        # restore_original_encoding()
        
        # 获取当前脚本的完整路径
        script = os.path.abspath(sys.argv[0])
        
        # 获取参数
        params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]])
        
        # 使用 ShellExecuteEx 请求管理员权限
        # SW_SHOWNORMAL = 1
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # lpOperation - 请求管理员权限
            sys.executable, # lpFile - Python 解释器
            f'"{script}" {params}',  # lpParameters - 脚本和参数
            None,           # lpDirectory
            1               # nShowCmd - SW_SHOWNORMAL
        )
        
        if ret > 32:  # ShellExecute 成功
            sys.exit(0)
        else:
            print(f"请求管理员权限失败，错误代码: {ret}")
            return False
            
    except Exception as e:
        print(f"请求管理员权限时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # 检查管理员权限
    if not is_admin():
        print("=" * 60)
        print("[!] 检测到未以管理员权限运行")
        print("PostMessage 输入需要管理员权限才能向游戏窗口发送消息")
        print("正在请求管理员权限...")
        print("=" * 60)
        
        # 在请求提权前先还原编码，避免新进程无法还原
        # restore_original_encoding()
        
        if run_as_admin():
            # 成功请求提权，当前进程将退出
            return
        else:
            print("=" * 60)
            print("❌ 无法获取管理员权限")
            print("请手动以管理员身份运行此脚本")
            print("=" * 60)
            input("按 Enter 键退出...")
            sys.exit(1)
    
    # 初始化日志系统
    log_file = tools.setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("MdaDuetAssistant Agent 启动")
    logger.info("=" * 60)
    logger.info("[OK] 以管理员权限运行")
    logger.info(f"脚本目录: {script_dir}")
    logger.info(f"工作目录: {os.getcwd()}")
    

    Toolkit.init_option("./")

    if len(sys.argv) < 2:
        logger.error("缺少 socket_id 参数")
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)
        
    socket_id = sys.argv[-1]
    logger.info(f"Socket ID: {socket_id}")

    try:
        logger.info("启动 AgentServer...")
        AgentServer.start_up(socket_id)
        logger.info("AgentServer 已启动，等待任务...")
        AgentServer.join()
        logger.info("AgentServer 正常退出")
    except Exception as e:
        logger.error(f"AgentServer 运行出错: {e}", exc_info=True)
        raise
    finally:
        logger.info("关闭 AgentServer...")
        AgentServer.shut_down()
        logger.info("=" * 60)
        logger.info("MdaDuetAssistant Agent 已退出")
        logger.info("=" * 60)
        
        # 还原原始编码
        # restore_original_encoding()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] 程序被用户中断")
        # restore_original_encoding()
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        # restore_original_encoding()
        sys.exit(1)
