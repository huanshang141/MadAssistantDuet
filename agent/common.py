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

# 导入全局配置
from config import GAME_CONFIG

# 获取日志记录器
logger = logging.getLogger(__name__)

@AgentServer.custom_action("ResetCharacterPosition")
class ResetCharacterPosition(CustomAction):
    """
    测试版：通过 Context.run_task 同步执行节点 "Reset_Entry"

    参数（可选）：
    {
      "pipeline_override": { ... }  # 用于覆盖的 JSON
    }
    成功返回 True（可在日志中查看 task_id），失败返回 False。
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        try:
            # 解析参数，取出 pipeline_override（可选）
            pipeline_override = {}
            if isinstance(argv.custom_action_param, str) and argv.custom_action_param.strip():
                try:
                    params = json.loads(argv.custom_action_param)
                    pipeline_override = params.get("pipeline_override", {}) or {}
                except json.JSONDecodeError:
                    logger.warning("[ResetCharacterPosition] custom_action_param 不是有效 JSON，忽略覆盖参数")
            elif isinstance(argv.custom_action_param, dict):
                pipeline_override = argv.custom_action_param.get("pipeline_override", {}) or {}

            logger.debug("=" * 60)
            logger.info("[ResetCharacterPosition] 通过 run_task 执行节点 'Reset_Entry'")
            if pipeline_override:
                logger.debug(f"  使用 pipeline_override: {list(pipeline_override.keys())}")

            # 同步执行任务：失败将返回 None，成功返回 TaskDetail
            task_detail = context.run_task("Reset_Entry", pipeline_override=pipeline_override)

            if not task_detail:
                logger.error("[ResetCharacterPosition] 任务执行失败 (task_id = None)")
                logger.debug("=" * 60)
                return False

            logger.info(f"[ResetCharacterPosition] 任务执行成功, task_id={task_detail.task_id}")
            logger.debug("=" * 60)
            return True

        except Exception as e:
            logger.error(f"[ResetCharacterPosition] 执行异常: {e}", exc_info=True)
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
        # 从参数中获取配置（仅需要: check_interval(float), total_timeout(float), target_node(list[str])）
        # 支持 JSON 字符串或字典，单位按秒传入，这里转换为毫秒以复用原实现
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

        # 允许浮点数（秒），内部转换为毫秒兼容现有逻辑
        check_interval = float(params.get("check_interval", 5000))
        total_timeout = float(params.get("total_timeout", 180000))


        target_nodes = params.get("target_node", ["again_for_win"])  # 要检测的目标节点（支持数组）
        if isinstance(target_nodes, str):
            target_nodes = [target_nodes]
        # 兼容：保留旧字段以不破坏后续逻辑（但不再依赖 override_next）
        interrupt_node = params.get("interrupt_node", "autoBattle_for_win")
        
        # 兼容旧配置：如果 target_node 是字符串，转换为数组
        if isinstance(target_nodes, str):
            target_nodes = [target_nodes]
        
        logger.info("=" * 50)
        logger.info("[AutoBattle] 开始战斗循环检测")
        logger.info(f"  检测间隔: {check_interval}ms, 总超时: {total_timeout}ms")
        # logger.info(f"  目标节点: {target_nodes}, 中断节点: {interrupt_node}")
        
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
                    logger.debug(f"[AutoBattle] -> 尝试识别节点: '{target_node}'")
                    # 新版 run_recognition 总是返回 RecognitionDetail，使用 .hit 判断是否命中
                    current_reco_result = context.run_recognition(target_node, image)

                    # RecognitionDetail.hit 表示是否命中；额外检查 box 保持向后兼容
                    if getattr(current_reco_result, "hit", False):
                        if current_reco_result.box and current_reco_result.box.w > 0 and current_reco_result.box.h > 0:
                            logger.info(f"[AutoBattle] -> [OK] 识别到节点: '{target_node}'")
                            detected_node = target_node
                            reco_result = current_reco_result
                            break
                        else:
                            # hit 为 True 但没有有效 box 时，也认为命中（容错）
                            logger.info(f"[AutoBattle] -> [OK] 识别到节点(无 box): '{target_node}'")
                            detected_node = target_node
                            reco_result = current_reco_result
                            break
                    else:
                        logger.debug(f"[AutoBattle] -> [X] 未识别到节点: '{target_node}'")
                
                # 检查是否有任何一个节点被识别到
                if detected_node:
                    # 新逻辑：直接返回 True，不再 override_next
                    return True
                else:
                    # 从全局配置获取自动战斗模式
                    auto_battle_mode = GAME_CONFIG.get("auto_battle_mode", 0)
                    
                    if auto_battle_mode == 0:
                        # 模式 0: 循环按 E 键（默认）
                        logger.debug(f"[AutoBattle] -> 模式 0: 执行自动战斗（按 E 键）")
                        click_job = context.tasker.controller.post_click_key(69)  # E 键
                        click_job.wait()
                    elif auto_battle_mode == 1:
                        # 模式 1: 什么也不做
                        logger.debug(f"[AutoBattle] -> 模式 1: 什么也不做，仅等待")
                    else:
                        logger.warning(f"[AutoBattle] -> 未知模式 {auto_battle_mode}，默认执行模式 0")
                        click_job = context.tasker.controller.post_click_key(69)  # E 键
                        click_job.wait()

                    # 等待检测间隔
                    logger.debug(f"[AutoBattle] -> 等待检测间隔 {check_interval}ms...")
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
        
        # 从全局配置获取战斗轮数，确保是整数且至少 1
        try:
            total_rounds = int(GAME_CONFIG.get("battle_rounds", 3))
        except Exception:
            total_rounds = 3
        if total_rounds < 1:
            total_rounds = 1

        round_timeout = params.get("round_timeout", 420000)  # 每轮超时 420s
        post_rounds = params.get("post_rounds", [])  # 每轮后的处理节点列表
        
        logger.info("=" * 50)
        logger.info("[MultiRoundsAutoBattle] 开始多轮自动战斗")
        logger.info(f"  总轮数: {total_rounds} (来自全局配置), 每轮超时: {round_timeout}ms")
        
        # 提前创建 AutoBattle 实例，避免在 total_rounds == 1 时未定义变量的问题
        auto_battle_action = AutoBattle()

        # 执行前 (total_rounds-1) 轮，每轮完成后执行 post_rounds
        for round_num in range(1, total_rounds):
            logger.info(f"[MultiRoundsAutoBattle] 第 {round_num}/{total_rounds} 轮战斗开始")

            result = auto_battle_action.run(context, argv)

            if not result:
                logger.error(f"[MultiRoundsAutoBattle] 第 {round_num} 轮战斗失败或超时，终止多轮战斗")
                return False

            logger.info(f"[MultiRoundsAutoBattle] 第 {round_num} 轮战斗完成")

            # 执行每轮后的处理节点（异步/同步由 context.run_task 决定）
            for post_node in post_rounds:
                try:
                    context.run_task(post_node)
                except Exception as e:
                    logger.warning(f"[MultiRoundsAutoBattle] 执行 post_round '{post_node}' 时出错: {e}")

        # 最后一轮（或仅有的一轮）
        last_result = auto_battle_action.run(context, argv)
        if not last_result:
            logger.error(f"[MultiRoundsAutoBattle] 最后一轮战斗失败或超时")
            return False
        logger.info(f"[MultiRoundsAutoBattle] [OK] 所有 {total_rounds} 轮战斗已完成")
        logger.info("=" * 50)
        return True