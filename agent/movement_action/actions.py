"""
自定义按键动作 (使用 MaaFramework 控制器 API)

本文件原先通过 PostMessage + 扫描码与窗口句柄交互, 现根据需求改为:
1. 移除 GameWindowAction 基类与窗口句柄查找逻辑
2. 不再使用 PostMessageInputHelper 封装, 直接调用 context.tasker.controller 提供的
    异步按键接口: post_key_down / post_key_up / post_click_key
3. 保持与原有参数格式兼容

注意: 这些接口返回 Job, 使用 .wait() 保证顺序与时序可靠。
"""

import json
import logging
import time
from maa.custom_action import CustomAction
from maa.context import Context
from maa.agent.agent_server import AgentServer
import win32con
import sys
import os

# 导入全局配置
from config import GAME_CONFIG

logger = logging.getLogger(__name__)

# 注意：闪避键现在直接使用虚拟键码(int),无需映射


########################
# 通用辅助函数 (方向 / 键名映射)
########################

def direction_to_vk(direction: str) -> int:
    """方向字符串转换为虚拟键码 (支持 WASD 与方向键)."""
    d = direction.lower()
    mapping = {
        'w': ord('W'),
        'a': ord('A'),
        's': ord('S'),
        'd': ord('D'),
        'up': win32con.VK_UP,
        'down': win32con.VK_DOWN,
        'left': win32con.VK_LEFT,
        'right': win32con.VK_RIGHT,
    }
    if d not in mapping:
        raise ValueError(f"不支持的方向: {direction}")
    return mapping[d]

def char_to_vk(char: str) -> int:
    if len(char) != 1:
        raise ValueError(f"char 必须是单个字符: {char}")
    return ord(char.upper())

def name_to_vk(name: str) -> int:
    n = name.lower()
    special = {
        'shift': win32con.VK_SHIFT,
        'ctrl': win32con.VK_CONTROL,
        'alt': win32con.VK_MENU,
        'space': win32con.VK_SPACE,
        'enter': win32con.VK_RETURN,
        'esc': 27,
        'tab': win32con.VK_TAB,
    }
    if n in special:
        return special[n]
    if len(name) == 1:
        return char_to_vk(name)
    raise ValueError(f"不支持的键名称: {name}")


def debug_controller_attributes(ctrl, logger_instance=None):
    """
    调试工具：打印控制器对象的所有属性
    
    Args:
        ctrl: 控制器对象
        logger_instance: 日志记录器，如果为 None 则使用 print
    """
    log_func = logger_instance.debug if logger_instance else print
    
    log_func("=" * 60)
    log_func(f"[DEBUG] 控制器对象类型: {type(ctrl)}")
    log_func(f"[DEBUG] 控制器对象: {ctrl}")
    log_func("=" * 60)
    
    # 列出所有属性
    attrs = dir(ctrl)
    log_func(f"[DEBUG] 控制器属性列表 ({len(attrs)} 个):")
    
    for attr in attrs:
        if not attr.startswith('_'):  # 先显示公开属性
            try:
                value = getattr(ctrl, attr)
                value_type = type(value).__name__
                
                # 对于整数类型，同时显示十六进制
                if isinstance(value, int):
                    if 0 < value <= 0xFFFFFFFF:
                        log_func(f"  {attr}: {value} (0x{value:08X}) [{value_type}] ← 可能是窗口句柄")
                    else:
                        log_func(f"  {attr}: {value} [{value_type}]")
                elif callable(value):
                    log_func(f"  {attr}: <method/function> [{value_type}]")
                elif len(str(value)) < 100:
                    log_func(f"  {attr}: {value} [{value_type}]")
                else:
                    log_func(f"  {attr}: <large object> [{value_type}]")
            except Exception as e:
                log_func(f"  {attr}: <无法访问: {e}>")
    
    # 再显示私有属性
    log_func("\n[DEBUG] 私有属性:")
    for attr in attrs:
        if attr.startswith('_') and not attr.startswith('__'):
            try:
                value = getattr(ctrl, attr)
                value_type = type(value).__name__
                
                if isinstance(value, int):
                    if 0 < value <= 0xFFFFFFFF:
                        log_func(f"  {attr}: {value} (0x{value:08X}) [{value_type}] ← 可能是窗口句柄")
                    else:
                        log_func(f"  {attr}: {value} [{value_type}]")
                elif callable(value):
                    log_func(f"  {attr}: <method/function> [{value_type}]")
                elif len(str(value)) < 100:
                    log_func(f"  {attr}: {value} [{value_type}]")
                else:
                    log_func(f"  {attr}: <large object> [{value_type}]")
            except Exception as e:
                log_func(f"  {attr}: <无法访问: {e}>")
    
    log_func("=" * 60)

@AgentServer.custom_action("RunWithShift")
class RunWithShift(CustomAction):
    """
    奔跑动作：先按下方向键,再按下闪避键(可配置),保持指定时长
    
    参数说明：
    {
        "direction": "w",      // 方向键：'w', 'a', 's', 'd' 或 'up', 'down', 'left', 'right'
        "duration": 2.0,       // 持续时长（秒）
        "dodge_delay": 0.05    // 按下方向键后,多久按下闪避键（秒）,默认 0.05
    }
    
    注意：使用的闪避键从全局配置 main.GAME_CONFIG["dodge_key"] 中读取
    """
    
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 解析参数
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[RunWithShift] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[RunWithShift] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        # 获取参数
        direction = params.get("direction", "w")
        duration = params.get("duration", 2.0)
        dodge_delay = params.get("dodge_delay", 0.05)
        
        # 从全局配置获取闪避键(现在是虚拟键码 int)
        dodge_vk = GAME_CONFIG.get("dodge_key", win32con.VK_SHIFT)
        
        logger.debug("=" * 60)
        logger.info(f"[RunWithShift] 开始奔跑")
        logger.debug(f"  方向: {direction}")
        logger.debug(f"  持续时长: {duration:.2f}秒")
        logger.debug(f"  闪避键延迟: {dodge_delay:.3f}秒")
        logger.debug(f"  使用闪避键: VK={dodge_vk} (0x{dodge_vk:02X})")
        
        try:
            controller = context.tasker.controller
            if logger.isEnabledFor(logging.DEBUG):
                debug_controller_attributes(controller, logger)

            direction_vk = direction_to_vk(direction)
            
            logger.debug(f"[RunWithShift] 方向键 VK={direction_vk}, 闪避键 VK={dodge_vk}")
            
            # 1. 按下方向键
            logger.debug(f"[RunWithShift] 步骤 1: 按下方向键 '{direction}'")
            controller.post_key_down(direction_vk).wait()
            
            # 2. 短暂延迟
            if dodge_delay > 0:
                logger.debug(f"[RunWithShift] 等待 {dodge_delay:.3f}秒...")
                time.sleep(dodge_delay)
            
            # 3. 按下闪避键
            logger.debug(f"[RunWithShift] 步骤 2: 按下闪避键 (VK=0x{dodge_vk:02X})")
            controller.post_key_down(dodge_vk).wait()
            
            # 4. 保持按下状态
            logger.debug(f"[RunWithShift] 步骤 3: 保持 {duration:.2f}秒...")
            time.sleep(duration)
            
            # 5. 释放闪避键
            logger.debug(f"[RunWithShift] 步骤 4: 释放闪避键")
            controller.post_key_up(dodge_vk).wait()
            
            # 6. 释放方向键
            logger.debug(f"[RunWithShift] 步骤 5: 释放方向键")
            controller.post_key_up(direction_vk).wait()
            
            logger.info(f"[RunWithShift] [OK] 完成奔跑 {duration:.2f}秒")
            logger.debug("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"[RunWithShift] 发生异常: {e}", exc_info=True)
            return False

@AgentServer.custom_action("LongPressKey")
class LongPressKey(CustomAction):
    """
    长按单个按键
    
    参数说明：
    {
        "key": "w",           // 按键：字符或虚拟键码
        "duration": 2.0       // 持续时长（秒）
    }
    """
    
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 解析参数
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[LongPressKey] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[LongPressKey] JSON 解析失败: {e}")
            return False
        
        # 获取参数
        key = params.get("key")
        duration = params.get("duration", 1.0)
        
        if not key:
            logger.error("[LongPressKey] 缺少参数 'key'")
            return False
        
        logger.info(f"[LongPressKey] 长按键 '{key}' 持续 {duration:.2f}秒")
        
        try:
            controller = context.tasker.controller
            if isinstance(key, int):
                vk_code = key
            elif isinstance(key, str):
                try:
                    vk_code = name_to_vk(key)
                except ValueError as e:
                    logger.error(f"[LongPressKey] {e}")
                    return False
            else:
                logger.error(f"[LongPressKey] 不支持的键类型: {key}")
                return False

            controller.post_key_down(vk_code).wait()
            time.sleep(duration)
            controller.post_key_up(vk_code).wait()
            
            logger.info(f"[LongPressKey] [OK] 完成长按")
            return True
            
        except Exception as e:
            logger.error(f"[LongPressKey] 发生异常: {e}", exc_info=True)
            return False

@AgentServer.custom_action("PressMultipleKeys")
class PressMultipleKeys(CustomAction):
    """
    同时按下多个按键
    
    参数说明：
    {
        "keys": ["w", "shift"],  // 按键列表
        "duration": 2.0          // 持续时长（秒）
    }
    """
    
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 解析参数
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[PressMultipleKeys] 参数类型错误")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[PressMultipleKeys] JSON 解析失败: {e}")
            return False
        
        # 获取参数
        keys = params.get("keys", [])
        duration = params.get("duration", 1.0)
        
        if not keys:
            logger.error("[PressMultipleKeys] 缺少参数 'keys'")
            return False
        
        logger.info(f"[PressMultipleKeys] 同时按下 {len(keys)} 个键，持续 {duration:.2f}秒")
        logger.debug(f"  按键列表: {keys}")
        
        try:
            controller = context.tasker.controller
            vk_codes = []
            for key in keys:
                if isinstance(key, int):
                    vk_codes.append(key)
                elif isinstance(key, str):
                    try:
                        vk_codes.append(name_to_vk(key))
                    except ValueError as e:
                        logger.error(f"[PressMultipleKeys] {e}")
                        return False
                else:
                    logger.error(f"[PressMultipleKeys] 不支持的键类型: {key}")
                    return False

            for vk in vk_codes:
                controller.post_key_down(vk).wait()
            time.sleep(duration)
            for vk in vk_codes:
                controller.post_key_up(vk).wait()
            
            logger.info(f"[PressMultipleKeys] [OK] 完成同时按键")
            return True
            
        except Exception as e:
            logger.error(f"[PressMultipleKeys] 发生异常: {e}", exc_info=True)
            return False

@AgentServer.custom_action("RunWithJump")
class RunWithJump(CustomAction):
    """
    边跑边跳动作：先按下方向键，延迟后按下闪避键（奔跑），然后周期性短按空格键（跳跃）
    
    参数说明：
    {
        "direction": "w",        // 方向键：'w', 'a', 's', 'd' 或 'up', 'down', 'left', 'right'
        "duration": 3.0,         // 总持续时长（秒）
        "dodge_delay": 0.05,     // 按下方向键后，多久按下闪避键（秒），默认 0.05
        "jump_interval": 0.5,    // 跳跃间隔（秒），默认 0.5 秒跳一次
        "jump_press_time": 0.1   // 每次跳跃按键时长（秒），默认 0.1 秒
    }
    
    注意：使用的闪避键从全局配置 main.GAME_CONFIG["dodge_key"] 中读取
    """
    
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 解析参数
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[RunWithJump] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[RunWithJump] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        # 获取参数
        direction = params.get("direction", "w")
        duration = params.get("duration", 3.0)
        dodge_delay = params.get("dodge_delay", 0.05)
        jump_interval = params.get("jump_interval", 0.5)
        jump_press_time = params.get("jump_press_time", 0.1)
        
        # 从全局配置获取闪避键(现在是虚拟键码 int)
        dodge_vk = GAME_CONFIG.get("dodge_key", win32con.VK_SHIFT)
        
        logger.debug("=" * 60)
        logger.info(f"[RunWithJump] 开始边跑边跳")
        logger.debug(f"  方向: {direction}")
        logger.debug(f"  总持续时长: {duration:.2f}秒")
        logger.debug(f"  闪避键延迟: {dodge_delay:.3f}秒")
        logger.debug(f"  跳跃间隔: {jump_interval:.2f}秒")
        logger.debug(f"  跳跃按键时长: {jump_press_time:.3f}秒")
        logger.debug(f"  使用闪避键: VK={dodge_vk} (0x{dodge_vk:02X})")
        
        try:
            controller = context.tasker.controller
            direction_vk = direction_to_vk(direction)
            
            logger.debug(f"[RunWithJump] 方向键 VK={direction_vk}, 闪避键 VK={dodge_vk}")
            
            # 1. 按下方向键
            logger.debug(f"[RunWithJump] 步骤 1: 按下方向键 '{direction}'")
            controller.post_key_down(direction_vk).wait()
            
            # 2. 短暂延迟后按下闪避键
            if dodge_delay > 0:
                logger.debug(f"[RunWithJump] 等待 {dodge_delay:.3f}秒...")
                time.sleep(dodge_delay)
            
            logger.debug(f"[RunWithJump] 步骤 2: 按下闪避键 (VK=0x{dodge_vk:02X})")
            controller.post_key_down(dodge_vk).wait()
            
            # 3. 周期性跳跃，直到总时长结束
            logger.debug(f"[RunWithJump] 步骤 3: 开始周期性跳跃...")
            start_time = time.time()
            jump_count = 0
            next_jump_time = start_time + jump_interval
            
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # 检查是否达到总时长
                if elapsed_time >= duration:
                    logger.debug(f"[RunWithJump] 达到总时长 {duration:.2f}秒，停止跳跃")
                    break
                
                # 检查是否该跳跃了
                if current_time >= next_jump_time:
                    jump_count += 1
                    remaining_time = duration - elapsed_time
                    logger.debug(f"[RunWithJump] -> 第 {jump_count} 次跳跃 (剩余: {remaining_time:.2f}秒)")
                    
                    # 按下空格键
                    controller.post_key_down(win32con.VK_SPACE).wait()
                    time.sleep(jump_press_time)
                    controller.post_key_up(win32con.VK_SPACE).wait()
                    
                    # 计算下一次跳跃时间
                    next_jump_time = current_time + jump_interval
                else:
                    # 短暂休眠，避免 CPU 占用过高
                    time.sleep(0.01)
            
            # 4. 释放闪避键
            logger.debug(f"[RunWithJump] 步骤 4: 释放闪避键")
            controller.post_key_up(dodge_vk).wait()
            
            # 5. 释放方向键
            logger.debug(f"[RunWithJump] 步骤 5: 释放方向键")
            controller.post_key_up(direction_vk).wait()
            
            logger.info(f"[RunWithJump] [OK] 完成边跑边跳 {duration:.2f}秒，共跳跃 {jump_count} 次")
            logger.debug("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"[RunWithJump] 发生异常: {e}", exc_info=True)
            # 尝试释放所有按键
            try:
                controller.post_key_up(win32con.VK_SPACE).wait()
                controller.post_key_up(dodge_vk).wait()
                controller.post_key_up(direction_vk).wait()
            except Exception:
                pass
            return False
