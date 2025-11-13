"""
皎皎币动作序列执行器 (使用 MaaFramework 控制器 API)

变更说明:
- 移除窗口句柄查找与 PostMessageInputHelper 依赖
- 使用 context.tasker.controller.post_key_down/post_key_up 执行动作
- 仍支持从 JSON 文件加载序列, 并保留对“闪避键(shift)”到全局配置的映射
"""

import json
import logging
import time
import os
from maa.custom_action import CustomAction
from maa.context import Context
from maa.agent.agent_server import AgentServer
import win32con
import sys

# 导入全局配置
from config import GAME_CONFIG

logger = logging.getLogger(__name__)

# 本文件不再使用 PostMessageInputHelper


########################
# 键名/方向 -> VK 辅助
########################

def _char_to_vk(ch: str) -> int:
    if len(ch) != 1:
        raise ValueError(f"char 必须是单个字符: {ch}")
    return ord(ch.upper())

def _name_to_vk(name: str, dodge_vk: int) -> int:
    n = name.lower()
    special = {
        "shift": dodge_vk,  # shift 按 JSON 语义映射为配置的闪避键
        "ctrl": win32con.VK_CONTROL,
        "alt": win32con.VK_MENU,
        "space": win32con.VK_SPACE,
        "enter": win32con.VK_RETURN,
        "esc": win32con.VK_ESCAPE,
        "tab": win32con.VK_TAB,
        "up": win32con.VK_UP,
        "down": win32con.VK_DOWN,
        "left": win32con.VK_LEFT,
        "right": win32con.VK_RIGHT,
    }
    if n in special:
        return special[n]
    if len(name) == 1:
        return _char_to_vk(name)
    raise ValueError(f"不支持的按键: {name}")

@AgentServer.custom_action("JsonActionSequence")
class JsonActionSequence(CustomAction):
    """
    从JSON文件加载动作序列
    支持 Pipeline V1 格式
    支持闪避键映射：将JSON中的"shift"映射为配置的闪避键
    
    使用示例 (Pipeline V1):
    {
        "recognition": "FeatureMatch",
        "template": ["JJcoin/map2_1a.jpg"],
        "roi": [21,111,315,277],
        "post_delay": 2000,
        "action": "Custom",
        "custom_action": "JsonActionSequence",
        "custom_action_param": "JJCoin_map2_1aend.json",
        "next": ["JJcoin_finish"]
    }
    """
    
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        """
        执行从JSON文件加载的动作序列
        支持 Pipeline V1 格式的参数传递
        支持闪避键映射
        """
        logger.info("=" * 60)
        
        try:
            # 在 Pipeline V1 中，参数直接通过 argv 传递
            # 我们需要检查 argv 的类型并提取参数
            json_file = None
            
            # 调试信息：打印 argv 的类型和内容
            logger.debug(f"[JsonActionSequence] argv 类型: {type(argv)}")
            logger.debug(f"[JsonActionSequence] argv 内容: {argv}")
            
            # 尝试不同的参数获取方式
            if hasattr(argv, 'custom_action_param') and argv.custom_action_param:
                # Pipeline V1 方式：直接通过 custom_action_param 传递
                json_file = argv.custom_action_param
                logger.debug(f"[JsonActionSequence] 使用 custom_action_param: {json_file}")
            elif hasattr(argv, 'param') and argv.param:
                # 备用方式：通过 param 字段传递
                json_file = argv.param
                logger.debug(f"[JsonActionSequence] 使用 param: {json_file}")
            elif isinstance(argv, str):
                # 如果 argv 本身就是字符串
                json_file = argv
                logger.debug(f"[JsonActionSequence] 使用 argv 字符串: {json_file}")
            else:
                # 尝试从其他可能的属性获取
                for attr in ['action_param', 'json_file', 'file']:
                    if hasattr(argv, attr) and getattr(argv, attr):
                        json_file = getattr(argv, attr)
                        logger.info(f"[JsonActionSequence] 使用 {attr}: {json_file}")
                        break
            
            if not json_file:
                logger.error("[JsonActionSequence] 无法从参数中获取 JSON 文件名")
                logger.info(f"[JsonActionSequence] 可用的属性: {[attr for attr in dir(argv) if not attr.startswith('_')]}")
                return False
            
            # 清理文件名：去除多余的引号
            json_file = self._clean_filename(json_file)
            logger.info(f"[JsonActionSequence] 清理后的文件名: {json_file}")
            
            logger.info(f"[JsonActionSequence] 从文件加载动作序列: {json_file}")
            
            # 构建完整的JSON文件路径
            json_file_path = self._get_json_file_path(json_file)
            if not json_file_path:
                logger.error(f"[JsonActionSequence] 无法找到JSON文件: {json_file}")
                return False
            
            # 加载JSON文件
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    sequence_data = json.load(f)
            except Exception as e:
                logger.error(f"[JsonActionSequence] 加载JSON文件失败: {e}")
                return False
            
            # 提取动作序列信息
            sequence_name = sequence_data.get("name", "未知序列")
            total_time = sequence_data.get("total_time", 0)
            actions = sequence_data.get("actions", [])
            
            if not actions:
                logger.error(f"[JsonActionSequence] JSON文件中没有动作序列: {sequence_name}")
                return False
            
            logger.info(f"[JsonActionSequence] 加载序列: {sequence_name}")
            logger.info(f"  总时长: {total_time:.3f}秒")
            logger.info(f"  动作数量: {len(actions)} 个")
            
            # 从全局配置获取闪避键
            dodge_vk = GAME_CONFIG.get("dodge_key", win32con.VK_SHIFT)
            logger.info(f"[JsonActionSequence] 使用闪避键: VK={dodge_vk} (0x{dodge_vk:02X}) - {self._vk_to_name(dodge_vk)}")
            
            # 处理动作序列，将按键字符串转换为虚拟键码，并映射闪避键
            processed_actions = self._process_actions(actions, dodge_vk)
            if processed_actions is None:
                return False
            
            # 执行动作序列
            success = self._execute_action_sequence(context, processed_actions, sequence_name)
            
            if success:
                logger.info(f"[JsonActionSequence] [OK] 动作序列 '{sequence_name}' 执行完成")
                logger.info("=" * 60)
            else:
                logger.error(f"[JsonActionSequence] [FAILED] 动作序列 '{sequence_name}' 执行失败")
                logger.info("=" * 60)
            
            return success
            
        except Exception as e:
            logger.error(f"[JsonActionSequence] 发生异常: {e}", exc_info=True)
            logger.info("=" * 60)
            return False
    
    def _clean_filename(self, filename):
        """
        清理文件名，去除多余的引号
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
        """
        if not isinstance(filename, str):
            return str(filename)
        
        # 去除字符串两端的空格和引号
        cleaned = filename.strip()
        
        # 如果文件名被引号包围，去除引号
        if (cleaned.startswith('"') and cleaned.endswith('"')) or \
           (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1]
        
        return cleaned
    
    def _get_json_file_path(self, json_file):
        """
        获取JSON文件的完整路径
        
        Args:
            json_file: JSON文件名或相对路径
            
        Returns:
            str: JSON文件的完整路径，如果找不到返回None
        """
        try:
            # 如果给出的是绝对路径，直接返回（如果存在）
            if os.path.isabs(json_file) and os.path.exists(json_file):
                return json_file

            candidates = []

            # 优先：使用运行时工作目录下的 agent/action_json（用户要求）
            cwd = os.getcwd()
            candidates.append(os.path.join(cwd, 'agent', 'action_json'))

            # 去重并按顺序检查候选目录
            seen = set()
            for cand in candidates:
                if not cand or cand in seen:
                    continue
                seen.add(cand)

                # 先检查目录是否存在并列出调试信息
                if not os.path.exists(cand):
                    logger.debug(f"[JsonActionSequence] 候选目录不存在: {cand}")
                    continue

                # 直接匹配给定文件名
                json_file_path = os.path.join(cand, json_file)
                if os.path.exists(json_file_path):
                    return json_file_path

                # 尝试追加 .json
                if not json_file.lower().endswith('.json'):
                    json_file_path = os.path.join(cand, json_file + '.json')
                    if os.path.exists(json_file_path):
                        return json_file_path

                # 列出目录内容供调试
                try:
                    files = os.listdir(cand)
                    logger.debug(f"[JsonActionSequence] 目录 {cand} 内容: {files}")
                except Exception:
                    logger.debug(f"[JsonActionSequence] 无法列出目录内容: {cand}")

            # 未找到
            logger.error(f"[JsonActionSequence] 无法找到JSON文件: {json_file}")
            logger.error(f"  已搜索候选目录 (优先 cwd\agent\actionJSON): {candidates}")
            return None

        except Exception as e:
            logger.error(f"[JsonActionSequence] 获取JSON文件路径失败: {e}")
            return None
    
    def _process_actions(self, actions, dodge_vk):
        """
        处理动作序列，将按键字符串转换为虚拟键码
        特别处理：将JSON中的"shift"映射为配置的闪避键
        
        Args:
            actions: 原始动作序列
            dodge_vk: 闪避键虚拟键码
            
            
        Returns:
            list: 处理后的动作序列，如果转换失败返回None
        """
        processed_actions = []
        
        for action in actions:
            processed_action = action.copy()
            key = action.get("key")
            
            # 如果按键是字符串，需要转换为虚拟键码
            if isinstance(key, str):
                # 特殊按键映射
                special_keys = {
                    "shift": dodge_vk,  # 关键：将"shift"映射为配置的闪避键
                    "ctrl": win32con.VK_CONTROL,
                    "alt": win32con.VK_MENU,
                    "space": win32con.VK_SPACE,
                    "enter": win32con.VK_RETURN,
                    "esc": win32con.VK_ESCAPE,
                    "tab": win32con.VK_TAB
                }
                
                key_lower = key.lower()
                
                # 检查是否为特殊按键
                if key_lower in special_keys:
                    processed_action["key"] = special_keys[key_lower]
                    # 记录闪避键映射信息
                    if key_lower == "shift":
                        logger.debug(f"[JsonActionSequence] 映射闪避键: 'shift' -> VK={dodge_vk} (0x{dodge_vk:02X})")
                else:
                    try:
                        vk_code = _name_to_vk(key_lower, dodge_vk)
                        processed_action["key"] = vk_code
                    except Exception as e:
                        logger.error(f"[JsonActionSequence] 转换按键 '{key}' 时发生异常: {e}")
                        return None
            
            # 如果按键已经是整数，保持不变
            processed_actions.append(processed_action)
        
        return processed_actions
    
    def _execute_action_sequence(self, context: Context, actions, sequence_name):
        """
        执行动作序列
        
        Args:
            
            actions: 动作序列列表
            sequence_name: 序列名称，用于日志
            
        Returns:
            bool: 执行是否成功
        """
        try:
            start_time = time.time()
            last_action_time = 0.0
            
            for i, action in enumerate(actions):
                action_time = action["time"]
                action_type = action["type"]
                key = action["key"]
                
                # 计算需要等待的时间
                wait_time = action_time - last_action_time
                
                # 等待到指定时间点
                if wait_time > 0:
                    logger.debug(f"[{sequence_name}] 动作 {i+1:2d}/{len(actions)}: 等待 {wait_time:.3f}秒")
                    time.sleep(wait_time)
                
                # 执行按键操作
                # current_relative_time = time.time() - start_time
                # logger.debug(f"[{sequence_name}] 动作 {i+1:2d}/{len(actions)}: {action_type:8} {self._key_to_str(key):5} "
                #           f"(计划: {action_time:6.3f}s, 实际: {current_relative_time:6.3f}s)")
                
                # 执行按键操作
                controller = context.tasker.controller
                if action_type == "key_down":
                    controller.post_key_down(key).wait()
                elif action_type == "key_up":
                    controller.post_key_up(key).wait()
                else:
                    logger.error(f"[{sequence_name}] 不支持的操作类型: {action_type}")
                    return False
                
                last_action_time = action_time
            
            # 检查总执行时间
            total_execution_time = time.time() - start_time
            last_action_time = actions[-1]["time"]
            time_difference = total_execution_time - last_action_time
            
            logger.info(f"[{sequence_name}] 执行完成统计:")
            logger.info(f"  计划总时间: {last_action_time:.3f}秒")
            logger.info(f"  实际总时间: {total_execution_time:.3f}秒")
            logger.info(f"  时间误差: {time_difference:+.3f}秒")
            
            if abs(time_difference) > 0.5:  # 允许0.5秒误差
                logger.warning(f"[{sequence_name}] 时间误差较大，建议优化系统负载")
            
            return True
            
        except Exception as e:
            logger.error(f"[{sequence_name}] 执行动作序列时发生异常: {e}", exc_info=True)
            return False
    
    def _key_to_str(self, key):
        """
        将虚拟键码转换为可读的字符串，用于日志输出
        
        Args:
            key: 虚拟键码或字符串
            
        Returns:
            str: 可读的按键名称
        """
        try:
            # 如果是字符串，直接返回
            if isinstance(key, str):
                return key
            
            # 如果是虚拟键码，转换为可读名称
            return self._vk_to_name(key)
                
        except Exception as e:
            logger.error(f"[JsonActionSequence] 按键转换失败: {key} -> {e}")
            return str(key)
    
    def _vk_to_name(self, vk_code):
        """
        将虚拟键码转换为可读的名称
        
        Args:
            vk_code: 虚拟键码
            
        Returns:
            str: 可读的按键名称
        """
        vk_to_name = {
            win32con.VK_SHIFT: "shift",
            win32con.VK_CONTROL: "ctrl",
            win32con.VK_MENU: "alt",
            win32con.VK_SPACE: "space",
            win32con.VK_RETURN: "enter",
            win32con.VK_ESCAPE: "esc",
            win32con.VK_TAB: "tab",
            0x57: "w",  # VK_W
            0x41: "a",  # VK_A
            0x53: "s",  # VK_S
            0x44: "d",  # VK_D
            win32con.VK_UP: "up",
            win32con.VK_DOWN: "down",
            win32con.VK_LEFT: "left",
            win32con.VK_RIGHT: "right",
            0x05: "鼠标侧键1",  # XButton1
            0x06: "鼠标侧键2",  # XButton2
            0x02: "鼠标右键",   # Right mouse button
            0x20: "空格键",    # Space
            0x11: "Ctrl键",    # Ctrl
            0x12: "Alt键",     # Alt
            0x35: "数字5键",   # 5 key
        }
        
        if vk_code in vk_to_name:
            return vk_to_name[vk_code]
        else:
            return f"0x{vk_code:02X}"