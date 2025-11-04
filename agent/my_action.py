from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time
import logging
import json

# 导入 PostMessage 相关的自定义动作
from postmessage.actions import RunWithShift, LongPressKey, PressMultipleKeys

# 获取日志记录器
logger = logging.getLogger(__name__)


@AgentServer.custom_action("SetDodgeKey")
class SetDodgeKey(CustomAction):
    """
    设置闪避键配置
    用于保存用户选择的闪避键到全局配置中
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        try:
            # 解析参数
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[SetDodgeKey] 参数类型错误: {type(argv.custom_action_param)}")
                return False
            
            # 获取闪避键虚拟键码(现在直接是 int)
            dodge_key_vk = params.get("dodge_key", 0x10)  # 默认 Shift = 0x10
            
            # 导入 main 模块以访问全局配置
            import main
            
            # 保存到全局配置
            main.GAME_CONFIG["dodge_key"] = dodge_key_vk
            
            logger.info(f"[SetDodgeKey] [OK] 闪避键已设置为: VK=0x{dodge_key_vk:02X} ({dodge_key_vk})")
            logger.info(f"[SetDodgeKey] 当前配置: {main.GAME_CONFIG}")
            
            # 强制刷新截图缓存，避免后续节点使用旧图
            logger.info(f"[SetDodgeKey] 刷新截图缓存...")
            screencap_job = context.tasker.controller.post_screencap()
            screencap_job.wait()
            logger.info(f"[SetDodgeKey] [OK] 截图缓存已更新")
            
            return True
            
        except Exception as e:
            logger.error(f"[SetDodgeKey] 发生异常: {e}", exc_info=True)
            return False


@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        logger.info("my_action_111 is running!")

        return True


@AgentServer.custom_action("LongPressWithTimeoutDetection")
class LongPressWithTimeoutDetection(CustomAction):
    """
    循环检测目标文字，支持超时处理和中断动作
    当未检测到目标时，执行中断动作（自动战斗）
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 从参数中获取配置
        # custom_action_param 是 JSON 字符串，需要解析为字典
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[LongPressWithTimeoutDetection] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[LongPressWithTimeoutDetection] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        check_interval = params.get("check_interval", 5000)  # 检测间隔
        total_timeout = params.get("total_timeout", 180000)  # 总超时时间 180s
        target_node = params.get("target_node", "again_for_win")  # 要检测的目标节点
        interrupt_node = params.get("interrupt_node", "autoBattle_for_win")  # 未检测到时的候补节点
        
        logger.info("=" * 50)
        logger.info("[LongPressWithTimeoutDetection] 开始战斗循环检测")
        logger.info(f"  检测间隔: {check_interval}ms, 总超时: {total_timeout}ms")
        logger.info(f"  目标节点: {target_node}, 中断节点: {interrupt_node}")
        
        try:
            # 开始循环检测目标节点
            start_time = time.time()
            loop_count = 0
            
            while True:
                loop_count += 1
                elapsed = (time.time() - start_time) * 1000  # 已经过的时间（毫秒）
                
                # 检查是否超时
                if elapsed >= total_timeout:
                    logger.warning(f"[LongPressWithTimeoutDetection] 超时 {total_timeout}ms，跳转到 on_error")
                    logger.info(f"  总循环次数: {loop_count}")
                    return False
                
                # 尝试检测目标节点
                logger.info(f"[LongPressWithTimeoutDetection] 第 {loop_count} 次检测 '{target_node}'... (已用时: {int(elapsed)}ms / {total_timeout}ms)")
                
                # 获取最新截图
                sync_job = context.tasker.controller.post_screencap()
                sync_job.wait()
                image = context.tasker.controller.cached_image  # 这是属性,不是方法
                
                # 运行目标节点的识别
                reco_result = context.run_recognition(target_node, image)
                
                # 检查识别结果是否有效（box 不为 None 且宽高大于 0）
                if reco_result and reco_result.box and reco_result.box.w > 0 and reco_result.box.h > 0:
                    logger.info(f"[LongPressWithTimeoutDetection] [OK] 检测到 '{target_node}'")
                    logger.info(f"  识别框: x={reco_result.box.x}, y={reco_result.box.y}, w={reco_result.box.w}, h={reco_result.box.h}")
                    logger.info(f"  识别算法: {reco_result.algorithm}")
                    logger.info(f"  总循环次数: {loop_count}, 总用时: {int(elapsed)}ms")
                    # 动态设置 next 节点
                    context.override_next(argv.node_name, [target_node])
                    return True
                else:
                    # 详细记录未识别的原因
                    if not reco_result:
                        logger.info(f"[LongPressWithTimeoutDetection] [X] 未检测到 '{target_node}' (reco_result 为 None)")
                    elif not reco_result.box:
                        logger.info(f"[LongPressWithTimeoutDetection] [X] 未检测到 '{target_node}' (box 为 None)")
                    else:
                        logger.info(f"[LongPressWithTimeoutDetection] [X] 未检测到 '{target_node}' (box 无效: w={reco_result.box.w}, h={reco_result.box.h})")
                    
                    logger.info(f"[LongPressWithTimeoutDetection] -> 执行 interrupt '{interrupt_node}'")
                    
                    # 直接执行 interrupt 节点的动作（按 E 键）
                    try:
                        # 获取 interrupt_node 的配置并执行
                        click_job = context.tasker.controller.post_click_key(69)  # E 键
                        click_job.wait()
                        logger.info(f"[LongPressWithTimeoutDetection] -> 执行了按键 E (自动战斗)")
                        
                        # 等待 interrupt 节点的 post_delay
                        # logger.info(f"[LongPressWithTimeoutDetection] -> 等待 5 秒...")
                        # time.sleep(5)  # autoBattle_for_win 的 post_delay 是 5000ms

                    except Exception as e:
                        logger.error(f"[LongPressWithTimeoutDetection] 执行 interrupt 节点出错: {e}", exc_info=True)
                    
                    # 等待检测间隔
                    logger.info(f"[LongPressWithTimeoutDetection] -> 等待检测间隔 {check_interval}ms...")
                    time.sleep(check_interval / 1000.0)
                    
        except Exception as e:
            logger.error(f"[LongPressWithTimeoutDetection] 发生异常: {e}", exc_info=True)
            return False


@AgentServer.custom_action("LongPressMultipleKeys")
class LongPressMultipleKeys(CustomAction):
    """
    同时长按多个按键
    支持同时按下多个键并保持指定时长
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 从参数中获取配置
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[LongPressMultipleKeys] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[LongPressMultipleKeys] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        # 获取参数
        keys = params.get("keys", [])  # 按键列表
        duration = params.get("duration", 1000)  # 持续时间（毫秒）
        
        if not keys or not isinstance(keys, list):
            logger.error(f"[LongPressMultipleKeys] 参数错误: keys 必须是非空列表，当前值: {keys}")
            return False
        
        logger.info("=" * 50)
        logger.info(f"[LongPressMultipleKeys] 开始同时长按多个按键")
        logger.info(f"  按键列表: {keys} (数量: {len(keys)})")
        logger.info(f"  持续时长: {duration}ms ({duration/1000:.1f}秒)")
        
        try:
            # 1. 按下所有键
            logger.info(f"[LongPressMultipleKeys] 步骤 1: 按下所有键...")
            down_jobs = []
            for key in keys:
                logger.info(f"  -> 按下键: {key}")
                job = context.tasker.controller.post_key_down(key)
                down_jobs.append(job)
            
            # 等待所有按键操作完成
            # for job in down_jobs:
            #     job.wait()
            
            # 2. 保持按下状态指定时长
            logger.info(f"[LongPressMultipleKeys] 步骤 2: 保持 {duration}ms...")
            time.sleep(duration / 1000.0)
            
            # 3. 释放所有键
            logger.info(f"[LongPressMultipleKeys] 步骤 3: 释放所有键...")
            up_jobs = []
            for key in keys:
                logger.info(f"  -> 释放键: {key}")
                job = context.tasker.controller.post_key_up(key)
                up_jobs.append(job)
            
            # 等待所有释放操作完成
            # for job in up_jobs:
            #     job.wait()
            
            logger.info(f"[LongPressMultipleKeys] [OK] 完成！同时长按 {len(keys)} 个键共 {duration}ms")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"[LongPressMultipleKeys] 发生异常: {e}", exc_info=True)
            return False


@AgentServer.custom_action("SequentialLongPress")
class SequentialLongPress(CustomAction):
    """
    顺序按下多个按键并长按，最后一起释放
    适用于需要先后按下不同键并保持的场景（如：先移动再冲刺）
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 从参数中获取配置
        try:
            if isinstance(argv.custom_action_param, str):
                params = json.loads(argv.custom_action_param)
            elif isinstance(argv.custom_action_param, dict):
                params = argv.custom_action_param
            else:
                logger.error(f"[SequentialLongPress] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[SequentialLongPress] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        # 获取参数
        key_sequence = params.get("key_sequence", [])  # 按键序列: [{key: 65, delay: 500}, ...]
        hold_duration = params.get("hold_duration", 1000)  # 保持时长（毫秒）
        
        if not key_sequence or not isinstance(key_sequence, list):
            logger.error(f"[SequentialLongPress] 参数错误: key_sequence 必须是非空列表")
            return False
        
        logger.info("=" * 50)
        logger.info(f"[SequentialLongPress] 开始顺序长按按键")
        logger.info(f"  按键序列: {key_sequence}")
        logger.info(f"  保持时长: {hold_duration}ms ({hold_duration/1000:.1f}秒)")
        
        try:
            pressed_keys = []  # 记录已按下的键
            
            # 步骤 1: 按顺序按下所有键
            logger.info(f"[SequentialLongPress] 步骤 1: 按顺序按下所有键...")
            for i, key_info in enumerate(key_sequence):
                key = key_info.get("key")
                delay = key_info.get("delay", 0)  # 按下此键前的延迟（毫秒）
                
                if delay > 0:
                    logger.info(f"  -> 等待 {delay}ms...")
                    time.sleep(delay / 1000.0)
                
                logger.info(f"  -> 按下键 {i+1}/{len(key_sequence)}: {key}")
                context.tasker.controller.post_key_down(key)
                pressed_keys.append(key)
            
            # 步骤 2: 保持所有键按下状态
            logger.info(f"[SequentialLongPress] 步骤 2: 保持所有键按下 {hold_duration}ms...")
            time.sleep(hold_duration / 1000.0)
            
            # 步骤 3: 一起释放所有键
            logger.info(f"[SequentialLongPress] 步骤 3: 释放所有键...")
            for key in pressed_keys:
                logger.info(f"  -> 释放键: {key}")
                context.tasker.controller.post_key_up(key)
            
            logger.info(f"[SequentialLongPress] [OK] 完成！顺序按下 {len(pressed_keys)} 个键，保持 {hold_duration}ms")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"[SequentialLongPress] 发生异常: {e}", exc_info=True)
            # 尝试释放所有已按下的键
            logger.info("[SequentialLongPress] 尝试释放所有已按下的键...")
            for key in pressed_keys:
                try:
                    context.tasker.controller.post_key_up(key)
                except:
                    pass
            return False


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
