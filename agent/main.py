import sys
import logging
import os
from datetime import datetime
from pathlib import Path
import locale
import codecs

# 保存原始编码设置
_original_encoding = None
_original_stdout_encoding = None
_original_stderr_encoding = None


def set_utf8_encoding():
    """设置系统编码为 UTF-8，并保存原始编码"""
    global _original_encoding, _original_stdout_encoding, _original_stderr_encoding
    
    try:
        # 保存原始的 locale 编码
        _original_encoding = locale.getpreferredencoding()
        
        # 保存原始的 stdout/stderr 编码
        _original_stdout_encoding = sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else None
        _original_stderr_encoding = sys.stderr.encoding if hasattr(sys.stderr, 'encoding') else None
        
        # 在 Windows 上设置控制台代码页为 UTF-8
        if sys.platform == 'win32':
            try:
                import ctypes
                # 保存原始代码页
                kernel32 = ctypes.windll.kernel32
                original_cp = kernel32.GetConsoleOutputCP()
                
                # 设置为 UTF-8 (代码页 65001)
                kernel32.SetConsoleOutputCP(65001)
                kernel32.SetConsoleCP(65001)
            except Exception as e:
                # 静默处理，稍后输出
                pass
        
        # 重新包装 stdout 和 stderr 为 UTF-8
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        
        # 现在可以安全地输出中文了
        print(f"[编码管理] 原始系统编码: {_original_encoding}")
        print(f"[编码管理] 原始 stdout 编码: {_original_stdout_encoding}")
        print(f"[编码管理] 原始 stderr 编码: {_original_stderr_encoding}")
        if sys.platform == 'win32':
            print(f"[编码管理] 已设置控制台代码页为 UTF-8 (65001)")
        print(f"[编码管理] [OK] UTF-8 编码设置完成")
        
    except Exception as e:
        # 这里也可以安全输出了
        print(f"[编码管理] [错误] 设置 UTF-8 编码时出错: {e}")
        import traceback
        traceback.print_exc()


def restore_original_encoding():
    """还原原始编码设置"""
    global _original_encoding, _original_stdout_encoding, _original_stderr_encoding
    
    try:
        if sys.platform == 'win32' and _original_encoding:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                
                # 尝试将编码名称转换回代码页
                # 常见映射（支持更多格式）
                encoding_to_cp = {
                    'gbk': 936,
                    'gb2312': 936,
                    'gb18030': 54936,
                    'cp936': 936,  # 添加 cp936 支持
                    'cp54936': 54936,
                    'big5': 950,
                    'cp950': 950,
                    'shift_jis': 932,
                    'cp932': 932,
                    'utf-8': 65001,
                    'utf8': 65001,
                    'cp65001': 65001,
                }
                
                # 清理编码名称（移除短横线、下划线，转小写）
                clean_encoding = _original_encoding.lower().replace('-', '').replace('_', '')
                cp = encoding_to_cp.get(clean_encoding)
                
                if cp:
                    kernel32.SetConsoleOutputCP(cp)
                    kernel32.SetConsoleCP(cp)
                    print(f"[编码管理] 已还原控制台代码页: {cp} ({_original_encoding})")
                else:
                    print(f"[编码管理] [警告] 无法映射编码 '{_original_encoding}' 到代码页，保持当前设置")
                    
            except Exception as e:
                print(f"[编码管理] [警告] 还原控制台代码页失败: {e}")
        
        print(f"[编码管理] [OK] 编码还原完成")
        
    except Exception as e:
        print(f"[编码管理] [错误] 还原编码时出错: {e}")


# 确保当前脚本所在目录在 Python 路径中
script_dir = Path(__file__).parent.absolute()
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 设置 UTF-8 编码（在所有导入之前）
set_utf8_encoding()
    
print(f"脚本目录: {script_dir}")
print(f"工作目录: {os.getcwd()}")
print(f"Python 路径: {sys.path[:3]}")  # 只打印前3个

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

# 全局配置变量
GAME_CONFIG = {
    # "dodge_key": win32con.VK_RBUTTON  # 默认闪避键为 右键 (0x02)
    "dodge_key": 160,  # 左 Shift 键 (0xA0)
    "auto_battle_mode": 0  # 自动战斗模式：0=循环按E键, 1=什么也不做
}

# 重要：必须在 AgentServer.start_up() 之前导入，以便装饰器注册自定义 Action 和 Recognition
import my_action
import my_reco
import common
import setting


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
        restore_original_encoding()
        
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


def setup_logging():
    """配置日志系统，将日志输出到文件和控制台"""
    # 创建日志目录
    log_dir = r".\logs_agent"
    os.makedirs(log_dir, exist_ok=True)
    
    # 生成日志文件名（按日期和时间）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"agent_{timestamp}.log")
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 文件处理器
            logging.FileHandler(log_file, encoding='utf-8'),
            # 控制台处理器
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已初始化，日志文件: {log_file}")
    
    return log_file


def main():
    # 检查管理员权限
    if not is_admin():
        print("=" * 60)
        print("[!] 检测到未以管理员权限运行")
        print("PostMessage 输入需要管理员权限才能向游戏窗口发送消息")
        print("正在请求管理员权限...")
        print("=" * 60)
        
        # 在请求提权前先还原编码，避免新进程无法还原
        restore_original_encoding()
        
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
    log_file = setup_logging()
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
        restore_original_encoding()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] 程序被用户中断")
        restore_original_encoding()
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        restore_original_encoding()
        sys.exit(1)
