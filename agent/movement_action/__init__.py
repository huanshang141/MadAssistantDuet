"""
PostMessage 自定义动作模块

说明: 旧版的 PostMessageInputHelper 已移除，
当前仅导出使用 Maa 控制器 API 的自定义动作。
"""

from .actions import RunWithShift, LongPressKey, PressMultipleKeys, RunWithJump
from .action_sequence import JsonActionSequence

__all__ = [
    'RunWithShift',
    'LongPressKey',
    'PressMultipleKeys',
    'RunWithJump',
    'JsonActionSequence',
]
