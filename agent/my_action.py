from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time
import logging
import json

# 导入 PostMessage 相关的自定义动作
from postmessage.actions import RunWithShift, LongPressKey, PressMultipleKeys, RunWithJump
from postmessage.JJcoin_action import JsonActionSequence

# 获取日志记录器
logger = logging.getLogger(__name__)



# ========== PostMessage 按键输入动作（支持扫描码） ==========

@AgentServer.custom_action("RunWithShift")
class RunWithShiftAction(RunWithShift):
    """
    奔跑动作：先按下方向键，再按下 Shift，保持指定时长
    使用 PostMessage + 扫描码实现，兼容性更好
    
    参数示例：
    {
        "direction": "w",      // 方向键：'w', 'a', 's', 'd' 或 'up', 'down', 'left', 'right'
        "duration": 2.0,       // 持续时长（秒）
        "shift_delay": 0.05    // 按下方向键后，多久按下 Shift（秒），默认 0.05
    }
    """
    pass


@AgentServer.custom_action("LongPressKey")
class LongPressKeyAction(LongPressKey):
    """
    长按单个按键
    使用 PostMessage + 扫描码实现
    
    参数示例：
    {
        "key": "w",           // 按键：字符或虚拟键码
        "duration": 2.0       // 持续时长（秒）
    }
    """
    pass


@AgentServer.custom_action("PressMultipleKeys")
class PressMultipleKeysAction(PressMultipleKeys):
    """
    同时按下多个按键
    使用 PostMessage + 扫描码实现
    
    参数示例：
    {
        "keys": ["w", "shift"],  // 按键列表
        "duration": 2.0          // 持续时长（秒）
    }
    """
    pass


@AgentServer.custom_action("RunWithJump")
class RunWithJumpAction(RunWithJump):
    """
    边跑边跳动作：先按下方向键，延迟后按下闪避键（奔跑），然后周期性短按空格键（跳跃）
    使用 PostMessage + 扫描码实现
    
    参数示例：
    {
        "direction": "w",        // 方向键：'w', 'a', 's', 'd' 或 'up', 'down', 'left', 'right'
        "duration": 3.0,         // 总持续时长（秒）
        "dodge_delay": 0.05,     // 按下方向键后，多久按下闪避键（秒），默认 0.05
        "jump_interval": 0.5,    // 跳跃间隔（秒），默认 0.5 秒跳一次
        "jump_press_time": 0.1   // 每次跳跃按键时长（秒），默认 0.1 秒
    }
    """
    pass


@AgentServer.custom_action("JsonActionSequence")
class JsonActionSequenceAction(JsonActionSequence):
    """
    使用 JSON 定义一系列动作并执行
    使用 PostMessage + 扫描码实现

    
    """
    pass