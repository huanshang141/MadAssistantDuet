# -*- coding: utf-8 -*-
"""
设置自定义动作中的参数
变相实现变量存储流水线中的某些全局设置
"""

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import logging
import json


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


@AgentServer.custom_action("SetAutoBattleMode")
class SetAutoBattleMode(CustomAction):
    """
    设置自动战斗模式配置
    用于保存用户选择的自动战斗模式到全局配置中
    
    参数说明：
    {
        "auto_battle_mode": 0  // 自动战斗模式：0=循环按E键（默认）, 1=什么也不做
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
                logger.error(f"[SetAutoBattleMode] 参数类型错误: {type(argv.custom_action_param)}")
                return False
            
            # 获取自动战斗模式（默认为 0）
            auto_battle_mode = params.get("auto_battle_mode", 0)
            
            # 验证模式值
            if auto_battle_mode not in [0, 1]:
                logger.error(f"[SetAutoBattleMode] 无效的模式值: {auto_battle_mode}，仅支持 0 或 1")
                return False
            
            # 导入 main 模块以访问全局配置
            import main
            
            # 保存到全局配置
            main.GAME_CONFIG["auto_battle_mode"] = auto_battle_mode
            
            mode_desc = "循环按E键" if auto_battle_mode == 0 else "什么也不做"
            logger.info(f"[SetAutoBattleMode] [OK] 自动战斗模式已设置为: {auto_battle_mode} ({mode_desc})")
            logger.info(f"[SetAutoBattleMode] 当前配置: {main.GAME_CONFIG}")
            
            # 强制刷新截图缓存，避免后续节点使用旧图
            logger.info(f"[SetAutoBattleMode] 刷新截图缓存...")
            screencap_job = context.tasker.controller.post_screencap()
            screencap_job.wait()
            logger.info(f"[SetAutoBattleMode] [OK] 截图缓存已更新")
            
            return True
            
        except Exception as e:
            logger.error(f"[SetAutoBattleMode] 发生异常: {e}", exc_info=True)
            return False


@AgentServer.custom_action("SetBattleRounds")
class SetBattleRounds(CustomAction):
    """
    设置战斗轮数配置
    用于保存用户选择的战斗轮数到全局配置中
    
    参数说明：
    {
        "battle_rounds": 3  // 战斗轮数：正整数（默认为 3）
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
                logger.error(f"[SetBattleRounds] 参数类型错误: {type(argv.custom_action_param)}")
                return False
            
            # 获取战斗轮数（默认为 3）
            battle_rounds = params.get("battle_rounds", 3)
            
            # 验证轮数值（必须是正整数）
            if not isinstance(battle_rounds, int) or battle_rounds <= 0:
                logger.error(f"[SetBattleRounds] 无效的轮数值: {battle_rounds}，必须是正整数")
                return False
            
            # 导入 main 模块以访问全局配置
            import main
            
            # 保存到全局配置
            main.GAME_CONFIG["battle_rounds"] = battle_rounds
            
            logger.info(f"[SetBattleRounds] [OK] 战斗轮数已设置为: {battle_rounds}")
            logger.info(f"[SetBattleRounds] 当前配置: {main.GAME_CONFIG}")
            
            # 强制刷新截图缓存，避免后续节点使用旧图
            logger.info(f"[SetBattleRounds] 刷新截图缓存...")
            screencap_job = context.tasker.controller.post_screencap()
            screencap_job.wait()
            logger.info(f"[SetBattleRounds] [OK] 截图缓存已更新")
            
            return True
            
        except Exception as e:
            logger.error(f"[SetBattleRounds] 发生异常: {e}", exc_info=True)
            return False
