# -*- coding: utf-8 -*-
"""
通用自定义动作模块
包含各种常用的自定义 Action
"""

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time
import logging
import json
import os
from datetime import datetime

# 获取日志记录器
logger = logging.getLogger(__name__)


@AgentServer.custom_action("ResetCharacterPosition")
class ResetCharacterPosition(CustomAction):
    """
    复位角色位置的自定义动作
    
    执行流程：
    1. 按 ESC 键打开菜单
    2. OCR 识别并点击"设置"
    3. 模板匹配并点击"其他.jpg"
    4. OCR 识别并点击"复位角色"
    5. OCR 识别并点击"确定"
    
    参数示例：
    {
        "template_path": "common/其他.png",  // 模板图片路径（可选，默认为"common/其他.png"）
        "wait_delay": 500,                   // 每步操作后的等待时间（毫秒，可选，默认500ms）
        "retry_times": 10,                   // 识别重试次数（可选，默认10次）
        "retry_interval": 500                // 重试间隔（毫秒，可选，默认500ms）
    }
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
                params = {}
            
            # 获取参数
            template_path = params.get("template_path", "common/其他.png")
            wait_delay = params.get("wait_delay", 500)  # 默认每步等待 500ms
            retry_times = params.get("retry_times", 10)  # 默认重试 10 次
            retry_interval = params.get("retry_interval", 500)  # 默认重试间隔 500ms
            
            logger.info("=" * 60)
            logger.info("[ResetCharacterPosition] 开始执行角色复位流程")
            logger.info(f"  模板图片: {template_path}")
            logger.info(f"  等待延迟: {wait_delay}ms")
            logger.info(f"  重试次数: {retry_times}")
            logger.info(f"  重试间隔: {retry_interval}ms")
            logger.info("=" * 60)
            
            # 步骤 1: 按 ESC 键
            if not self._step1_press_esc(context, wait_delay):
                return False
            
            # 步骤 2: OCR 识别并点击"设置"
            if not self._step2_click_settings(context, wait_delay, retry_times, retry_interval):
                return False
            
            # 步骤 3: 模板匹配并点击"其他"
            if not self._step3_click_other(context, template_path, wait_delay, retry_times, retry_interval):
                return False
            
            # 步骤 4: OCR 识别并点击"复位角色"
            if not self._step4_click_reset_character(context, wait_delay, retry_times, retry_interval):
                return False
            
            # 步骤 5: OCR 识别并点击"确定"
            if not self._step5_click_confirm(context, wait_delay, retry_times, retry_interval):
                return False
            
            logger.info("[ResetCharacterPosition] [OK] 角色复位流程执行完成")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"[ResetCharacterPosition] 执行失败: {e}", exc_info=True)
            return False
    
    def _step1_press_esc(self, context: Context, wait_delay: int) -> bool:
        """步骤 1: 按 ESC 键打开菜单"""
        logger.info("[ResetCharacterPosition] 步骤 1: 按 ESC 键...")
        
        try:
            # ESC 键的虚拟键码是 27
            logger.info(f"  [DEBUG] 调用 post_click_key(27)...")
            click_job = context.tasker.controller.post_click_key(27)
            click_job.wait()
            logger.info(f"  [DEBUG] post_click_key(27) 完成")
            
            logger.info(f"  [OK] ESC 键已按下，等待 {wait_delay}ms...")
            time.sleep(wait_delay / 1000.0)
            
            # 刷新截图
            context.tasker.controller.post_screencap().wait()
            
            return True
            
        except Exception as e:
            logger.error(f"  [X] 按 ESC 键失败: {e}", exc_info=True)
            return False
    
    def _step2_click_settings(self, context: Context, wait_delay: int, retry_times: int, retry_interval: int) -> bool:
        """步骤 2: OCR 识别并点击"设置" (带重试机制，每次重试尝试两种识别方式)"""
        logger.info("[ResetCharacterPosition] 步骤 2: 识别并点击'设置'...")
        
        for attempt in range(1, retry_times + 1):
            try:
                logger.info(f"  尝试 {attempt}/{retry_times}: 识别'设置'...")
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                image = context.tasker.controller.cached_image
                
                # 定义要尝试的识别节点列表
                recognition_nodes = ["OCR_Settings", "Template_Match_Setting"]
                reco_result = None
                detected_method = None
                
                # 依次尝试两种识别方式
                for node_name in recognition_nodes:
                    logger.info(f"  -> 尝试识别方式: '{node_name}'")
                    current_reco_result = context.run_recognition(node_name, image)
                    
                    # 检查识别结果是否有效
                    if current_reco_result and current_reco_result.box and current_reco_result.box.w > 0:
                        logger.info(f"  -> [OK] 通过 '{node_name}' 识别成功")
                        reco_result = current_reco_result
                        detected_method = node_name
                        break
                    else:
                        logger.info(f"  -> [X] 通过 '{node_name}' 未识别到")
                
                # 检查是否有任何一种方式识别成功
                if not reco_result or not reco_result.box or reco_result.box.w == 0:
                    logger.warning(f"  尝试 {attempt}/{retry_times}: 两种方式均未找到'设置'")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_times:
                        logger.info(f"  等待 {retry_interval}ms 后重试...")
                        time.sleep(retry_interval / 1000.0)
                        continue
                    else:
                        logger.error(f"  [X] 已达最大重试次数 ({retry_times})")
                        return False
                
                logger.info(f"  [OK] 找到'设置' (通过 {detected_method}): box=({reco_result.box.x}, {reco_result.box.y}, {reco_result.box.w}, {reco_result.box.h})")
                time.sleep(0.5) 
                
                # 点击识别框的中心
                click_x = reco_result.box.x + reco_result.box.w // 2
                click_y = reco_result.box.y + reco_result.box.h // 2
                
                click_job = context.tasker.controller.post_click(click_x, click_y)
                click_job.wait()
                
                logger.info(f"  [OK] 已点击'设置'，等待 {wait_delay}ms...")
                time.sleep(wait_delay / 1000.0)
                
                # 刷新截图 - 添加延迟确保缓存更新
                context.tasker.controller.post_screencap().wait()
                
                return True
                
            except Exception as e:
                logger.error(f"  尝试 {attempt}/{retry_times} [X] 点击'设置'失败: {e}", exc_info=True)
                if attempt < retry_times:
                    time.sleep(retry_interval / 1000.0)
                else:
                    return False
        
        return False
    
    def _step3_click_other(self, context: Context, template_path: str, wait_delay: int, retry_times: int, retry_interval: int) -> bool:
        """步骤 3: 模板匹配并点击"其他" (带重试机制)"""
        logger.info(f"[ResetCharacterPosition] 步骤 3: 模板匹配并点击'{template_path}'...")
        
        for attempt in range(1, retry_times + 1):
            try:
                logger.info(f"  尝试 {attempt}/{retry_times}: 模板匹配'{template_path}'...")
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                image = context.tasker.controller.cached_image
                
                # 使用预定义节点 Template_Other (在 resetPosition.json 中定义)
                # 如果需要动态模板路径,使用 pipeline_override 覆盖
                reco_result = context.run_recognition(
                    "Template_Other",
                    image,
                    pipeline_override={
                        "Template_Other": {
                            "template": template_path
                        }
                    } if template_path != "common/其他.png" else {}
                )
                
                if not reco_result or not reco_result.box or reco_result.box.w == 0:
                    logger.warning(f"  尝试 {attempt}/{retry_times}: 未找到模板'{template_path}'")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_times:
                        logger.info(f"  等待 {retry_interval}ms 后重试...")
                        time.sleep(retry_interval / 1000.0)
                        continue
                    else:
                        logger.error(f"  [X] 已达最大重试次数 ({retry_times})")
                        return False
                
                logger.info(f"  [OK] 找到模板: box=({reco_result.box.x}, {reco_result.box.y}, {reco_result.box.w}, {reco_result.box.h})")
                
                time.sleep(0.5) 

                # 点击识别框的中心
                click_x = reco_result.box.x + reco_result.box.w // 2
                click_y = reco_result.box.y + reco_result.box.h // 2
                
                click_job = context.tasker.controller.post_click(click_x, click_y)
                click_job.wait()
                
                logger.info(f"  [OK] 已点击'{template_path}'，等待 {wait_delay}ms...")
                time.sleep(wait_delay / 1000.0)
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                return True
                
            except Exception as e:
                logger.error(f"  尝试 {attempt}/{retry_times} [X] 点击'{template_path}'失败: {e}", exc_info=True)
                if attempt < retry_times:
                    time.sleep(retry_interval / 1000.0)
                else:
                    return False
        
        return False
    
    def _step4_click_reset_character(self, context: Context, wait_delay: int, retry_times: int, retry_interval: int) -> bool:
        """步骤 4: OCR 识别并点击"复位角色" (带重试机制)"""
        logger.info("[ResetCharacterPosition] 步骤 4: OCR 识别并点击'复位角色'...")
        
        for attempt in range(1, retry_times + 1):
            try:
                logger.info(f"  尝试 {attempt}/{retry_times}: OCR 识别'复位角色'...")
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                image = context.tasker.controller.cached_image
                
                # 使用预定义节点 OCR_ResetCharacter (在 resetPosition.json 中定义)
                reco_result = context.run_recognition(
                    "OCR_ResetCharacter",
                    image
                )
                
                if not reco_result or not reco_result.box or reco_result.box.w == 0:
                    logger.warning(f"  尝试 {attempt}/{retry_times}: 未找到'复位角色'文字")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_times:
                        logger.info(f"  等待 {retry_interval}ms 后重试...")
                        time.sleep(retry_interval / 1000.0)
                        continue
                    else:
                        logger.error(f"  [X] 已达最大重试次数 ({retry_times})")
                        return False
                
                logger.info(f"  [OK] 找到'复位角色': box=({reco_result.box.x}, {reco_result.box.y}, {reco_result.box.w}, {reco_result.box.h})")
                
                time.sleep(0.5) 

                # 点击识别框的中心
                click_x = reco_result.box.x + reco_result.box.w // 2
                click_y = reco_result.box.y + reco_result.box.h // 2
                
                click_job = context.tasker.controller.post_click(click_x, click_y)
                click_job.wait()
                
                logger.info(f"  [OK] 已点击'复位角色'，等待 {wait_delay}ms...")
                time.sleep(wait_delay / 1000.0)
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                return True
                
            except Exception as e:
                logger.error(f"  尝试 {attempt}/{retry_times} [X] 点击'复位角色'失败: {e}", exc_info=True)
                if attempt < retry_times:
                    time.sleep(retry_interval / 1000.0)
                else:
                    return False
        
        return False
    
    def _step5_click_confirm(self, context: Context, wait_delay: int, retry_times: int, retry_interval: int) -> bool:
        """步骤 5: OCR 识别并点击"确定" (带重试机制)"""
        logger.info("[ResetCharacterPosition] 步骤 5: OCR 识别并点击'确定'...")
        
        for attempt in range(1, retry_times + 1):
            try:
                logger.info(f"  尝试 {attempt}/{retry_times}: OCR 识别'确定'...")
                
                # 刷新截图
                context.tasker.controller.post_screencap().wait()
                image = context.tasker.controller.cached_image
                reco_result = context.run_recognition(
                    "OCR_Confirm",
                    image
                )
                
                if not reco_result or not reco_result.box or reco_result.box.w == 0:
                    logger.warning(f"  尝试 {attempt}/{retry_times}: 未找到'确定'文字")
                    
                    # 如果不是最后一次尝试，等待后重试
                    if attempt < retry_times:
                        logger.info(f"  等待 {retry_interval}ms 后重试...")
                        time.sleep(retry_interval / 1000.0)
                        continue
                    else:
                        logger.error(f"  [X] 已达最大重试次数 ({retry_times})")
                        return False
                
                logger.info(f"  [OK] 找到'确定': box=({reco_result.box.x}, {reco_result.box.y}, {reco_result.box.w}, {reco_result.box.h})")
                
                time.sleep(0.5)
                
                # 点击识别框的中心
                click_x = reco_result.box.x + reco_result.box.w // 2
                click_y = reco_result.box.y + reco_result.box.h // 2
                
                click_job = context.tasker.controller.post_click(click_x, click_y)
                click_job.wait()
                
                logger.info(f"  [OK] 已点击'确定'，等待 {wait_delay}ms...")
                time.sleep(wait_delay / 1000.0)
                
                # 刷新截图 - 添加延迟确保缓存更新
                context.tasker.controller.post_screencap().wait()
                time.sleep(0.1)  # 等待控制器缓存更新
                
                return True
                
            except Exception as e:
                logger.error(f"  尝试 {attempt}/{retry_times} [X] 点击'确定'失败: {e}", exc_info=True)
                if attempt < retry_times:
                    time.sleep(retry_interval / 1000.0)
                else:
                    return False
        
        return False

@AgentServer.custom_action("AutoBattle")
class AutoBattle(CustomAction):
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
                logger.error(f"[AutoBattle] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[AutoBattle] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        check_interval = params.get("check_interval", 5000)  # 检测间隔
        total_timeout = params.get("total_timeout", 180000)  # 总超时时间 180s
        target_nodes = params.get("target_node", ["again_for_win"])  # 要检测的目标节点（支持数组）
        interrupt_node = params.get("interrupt_node", "autoBattle_for_win")  # 未检测到时的候补节点
        
        # 兼容旧配置：如果 target_node 是字符串，转换为数组
        if isinstance(target_nodes, str):
            target_nodes = [target_nodes]
        
        logger.info("=" * 50)
        logger.info("[AutoBattle] 开始战斗循环检测")
        logger.info(f"  检测间隔: {check_interval}ms, 总超时: {total_timeout}ms")
        logger.info(f"  目标节点: {target_nodes}, 中断节点: {interrupt_node}")
        
        try:
            # 开始循环检测目标节点
            start_time = time.time()
            loop_count = 0
            
            while True:
                if context.tasker.stopping:
                    logger.info("[AutoBattle] 任务暂停")
                    return False
                loop_count += 1
                elapsed = (time.time() - start_time) * 1000  # 已经过的时间（毫秒）
                
                # 检查是否超时
                if elapsed >= total_timeout:
                    logger.warning(f"[AutoBattle] 超时 {total_timeout}ms，跳转到 on_error")
                    logger.info(f"  总循环次数: {loop_count}")
                    return False
                
                # 尝试检测目标节点
                logger.info(f"[AutoBattle] 第 {loop_count} 次检测 {target_nodes}... (已用时: {int(elapsed)}ms / {total_timeout}ms)")
                
                # 获取最新截图
                sync_job = context.tasker.controller.post_screencap()
                sync_job.wait()
                image = context.tasker.controller.cached_image  # 这是属性,不是方法
                
                # 依次对所有目标节点进行识别
                detected_node = None
                reco_result = None
                
                for target_node in target_nodes:
                    logger.info(f"[AutoBattle] -> 尝试识别节点: '{target_node}'")
                    current_reco_result = context.run_recognition(target_node, image)
                    
                    # 检查识别结果是否有效（box 不为 None 且宽高大于 0）
                    if current_reco_result and current_reco_result.box and current_reco_result.box.w > 0 and current_reco_result.box.h > 0:
                        logger.info(f"[AutoBattle] -> [OK] 识别到节点: '{target_node}'")
                        detected_node = target_node
                        reco_result = current_reco_result
                        break
                    else:
                        logger.info(f"[AutoBattle] -> [X] 未识别到节点: '{target_node}'")
                
                # 检查是否有任何一个节点被识别到
                if detected_node:
                    logger.info(f"[AutoBattle] [OK] 检测到 '{detected_node}'")
                    logger.info(f"  识别框: x={reco_result.box.x}, y={reco_result.box.y}, w={reco_result.box.w}, h={reco_result.box.h}")
                    logger.info(f"  识别算法: {reco_result.algorithm}")
                    logger.info(f"  总循环次数: {loop_count}, 总用时: {int(elapsed)}ms")
                    # 动态设置 next 节点
                    context.override_next(argv.node_name, [detected_node])
                    return True
                else:
                    # 所有节点都未识别到
                    logger.info(f"[AutoBattle] [X] 未检测到任何目标节点 {target_nodes}")
                    
                    logger.info(f"[AutoBattle] -> 执行 interrupt '{interrupt_node}'")
                 
                    # 从全局配置获取自动战斗模式
                    import main
                    auto_battle_mode = main.GAME_CONFIG.get("auto_battle_mode", 0)
                    
                    if auto_battle_mode == 0:
                        # 模式 0: 循环按 E 键（默认）
                        logger.info(f"[AutoBattle] -> 模式 0: 执行自动战斗（按 E 键）")
                        click_job = context.tasker.controller.post_click_key(69)  # E 键
                        click_job.wait()
                    elif auto_battle_mode == 1:
                        # 模式 1: 什么也不做
                        logger.info(f"[AutoBattle] -> 模式 1: 什么也不做，仅等待")
                    else:
                        logger.warning(f"[AutoBattle] -> 未知模式 {auto_battle_mode}，默认执行模式 0")
                        click_job = context.tasker.controller.post_click_key(69)  # E 键
                        click_job.wait()

                    # 等待检测间隔
                    logger.info(f"[AutoBattle] -> 等待检测间隔 {check_interval}ms...")
                    time.sleep(check_interval / 1000.0)
                    
        except Exception as e:
            logger.error(f"[AutoBattle] 发生异常: {e}", exc_info=True)
            return False

@AgentServer.custom_action("MultiRoundsAutoBattle")
class MultiRoundsAutoBattle(CustomAction):
    """
    多轮自动战斗动作
    循环执行 AutoBattle，直到达到指定轮数或超时
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
                logger.error(f"[MultiRoundsAutoBattle] 参数类型错误: {type(argv.custom_action_param)}")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"[MultiRoundsAutoBattle] JSON 解析失败: {e}")
            logger.error(f"  参数内容: {argv.custom_action_param}")
            return False
        
        # 从全局配置获取战斗轮数
        import main
        total_rounds = main.GAME_CONFIG.get("battle_rounds", 3)  # 默认 3 轮
        round_timeout = params.get("round_timeout", 420000)  # 每轮超时 420s
        post_rounds = params.get("post_rounds", [])  # 每轮后的处理节点列表
        
        logger.info("=" * 50)
        logger.info("[MultiRoundsAutoBattle] 开始多轮自动战斗")
        logger.info(f"  总轮数: {total_rounds} (来自全局配置), 每轮超时: {round_timeout}ms")
        
        for round_num in range(1, total_rounds + 1):
            logger.info(f"[MultiRoundsAutoBattle] 第 {round_num}/{total_rounds} 轮战斗开始")
            
            # 执行 AutoBattle 动作
            auto_battle_action = AutoBattle()

            # action_argv = CustomAction.RunArg(
            #     node_name=argv.node_name,
            #     custom_action_param=json.dumps({
            #         "check_interval": params.get("check_interval", 5000),
            #         "total_timeout": round_timeout,
            #         "target_node": params.get("target_node"),
            #         "interrupt_node": params.get("interrupt_node", "autoBattle_for_win")
            #     })
            # )
            
            result = auto_battle_action.run(context, argv)
            
            if not result:
                logger.error(f"[MultiRoundsAutoBattle] 第 {round_num} 轮战斗失败或超时，终止多轮战斗")
                return False

            logger.info(f"[MultiRoundsAutoBattle] 第 {round_num} 轮战斗完成")

            # 执行每轮后的处理节点
            for post_node in post_rounds:
                logger.info(f"[MultiRoundsAutoBattle] 执行每轮后的处理节点: '{post_node}'")
                task_detail = context.run_task(post_node)
                # if task_detail:
                #     # 等待任务完成
                #     job = context.tasker.get_latest_task_job()
                #     if job:
                #         job.wait()
                #         logger.info(f"[MultiRoundsAutoBattle] 处理节点 '{post_node}' 执行完成")
                # else:
                #     logger.warning(f"[MultiRoundsAutoBattle] 处理节点 '{post_node}' 启动失败")
        
        logger.info(f"[MultiRoundsAutoBattle] [OK] 所有 {total_rounds} 轮战斗已完成")
        logger.info("=" * 50)
        return True