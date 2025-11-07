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
    """设置系统编码为 GBK，并保存原始编码"""
    global _original_encoding, _original_stdout_encoding, _original_stderr_encoding
    
    try:
        # 保存原始的 locale 编码
        _original_encoding = locale.getpreferredencoding()
        
        # 保存原始的 stdout/stderr 编码
        _original_stdout_encoding = sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else None
        _original_stderr_encoding = sys.stderr.encoding if hasattr(sys.stderr, 'encoding') else None
        
        # 在 Windows 上设置控制台代码页为 GBK
        if sys.platform == 'win32':
            try:
                import ctypes
                # 保存原始代码页
                kernel32 = ctypes.windll.kernel32
                original_cp = kernel32.GetConsoleOutputCP()
                
                # 设置为 GBK (代码页 936)
                kernel32.SetConsoleOutputCP(936)
                kernel32.SetConsoleCP(936)
            except Exception as e:
                # 静默处理，稍后输出
                pass
        
        # 重新包装 stdout 和 stderr 为 GBK
        if sys.stdout.encoding not in ['gbk', 'cp936', 'gb2312']:
            sys.stdout = codecs.getwriter('gbk')(sys.stdout.detach())
        
        if sys.stderr.encoding not in ['gbk', 'cp936', 'gb2312']:
            sys.stderr = codecs.getwriter('gbk')(sys.stderr.detach())
        
        # 现在可以安全地输出中文了
        print(f"[编码管理] 原始系统编码: {_original_encoding}")
        print(f"[编码管理] 原始 stdout 编码: {_original_stdout_encoding}")
        print(f"[编码管理] 原始 stderr 编码: {_original_stderr_encoding}")
        if sys.platform == 'win32':
            print(f"[编码管理] 已设置控制台代码页为 GBK (936)")
        print(f"[编码管理] [OK] GBK 编码设置完成")
        
    except Exception as e:
        # 这里也可以安全输出了
        print(f"[编码管理] [错误] 设置 GBK 编码时出错: {e}")
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