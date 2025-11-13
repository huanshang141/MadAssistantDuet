"""
PostMessage 输入功能测试示例
演示如何在 pipeline 中使用 RunWithShift 等自定义动作
"""

import json

# ========== Pipeline 配置示例 ==========

pipeline_example = {
    "Entry": {
        "next": [
            "Test_Run_Forward",
            "Test_Run_Left", 
            "Test_Hold_Space",
            "Test_Multiple_Keys"
        ]
    },
    
    # 示例 1: 向前奔跑 3 秒
    "Test_Run_Forward": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {
            "direction": "w",      # W 键向前
            "duration": 3.0,       # 持续 3 秒
            "shift_delay": 0.05    # 按下 W 后 0.05 秒按下 Shift
        },
        "next": ["Test_Run_Left"]
    },
    
    # 示例 2: 向左奔跑 2 秒
    "Test_Run_Left": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {
            "direction": "a",      # A 键向左
            "duration": 2.0,
            "shift_delay": 0.1     # 稍长的延迟
        },
        "next": ["Test_Hold_Space"]
    },
    
    # 示例 3: 长按空格键 1.5 秒
    "Test_Hold_Space": {
        "recognition": "DirectHit",
        "action": "LongPressKey",
        "action_param": {
            "key": "space",        # 空格键
            "duration": 1.5
        },
        "next": ["Test_Multiple_Keys"]
    },
    
    # 示例 4: 同时按下 W + Shift 2 秒
    "Test_Multiple_Keys": {
        "recognition": "DirectHit",
        "action": "PressMultipleKeys",
        "action_param": {
            "keys": ["w", "shift"],
            "duration": 2.0
        }
    }
}

# ========== 更多场景示例 ==========

# 游戏场景 1: 连续移动和跳跃
game_sequence_1 = {
    "Move_And_Jump": {
        "next": ["Run_Forward", "Jump", "Run_Back"]
    },
    
    "Run_Forward": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {
            "direction": "w",
            "duration": 2.0
        },
        "next": ["Jump"]
    },
    
    "Jump": {
        "recognition": "DirectHit",
        "action": "LongPressKey",
        "action_param": {
            "key": "space",
            "duration": 0.3
        },
        "next": ["Run_Back"]
    },
    
    "Run_Back": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {
            "direction": "s",
            "duration": 1.5
        }
    }
}

# 游戏场景 2: 战斗组合技
combat_combo = {
    "Combat_Combo": {
        "next": ["Skill_1", "Skill_2", "Ultimate"]
    },
    
    "Skill_1": {
        "recognition": "DirectHit",
        "action": "LongPressKey",
        "action_param": {
            "key": "q",
            "duration": 1.0
        },
        "next": ["Skill_2"]
    },
    
    "Skill_2": {
        "recognition": "DirectHit",
        "action": "PressMultipleKeys",
        "action_param": {
            "keys": ["e", "shift"],
            "duration": 1.5
        },
        "next": ["Ultimate"]
    },
    
    "Ultimate": {
        "recognition": "DirectHit",
        "action": "LongPressKey",
        "action_param": {
            "key": "r",
            "duration": 2.0
        }
    }
}

# 游戏场景 3: 复杂移动路径
complex_movement = {
    "Complex_Path": {
        "next": [
            "Move_NE",    # 东北方向
            "Move_SW",    # 西南方向
            "Circle_Move" # 绕圈
        ]
    },
    
    # 东北方向奔跑（W + D）
    "Move_NE": {
        "recognition": "DirectHit",
        "action": "PressMultipleKeys",
        "action_param": {
            "keys": ["w", "d", "shift"],
            "duration": 2.0
        },
        "next": ["Move_SW"]
    },
    
    # 西南方向奔跑（S + A）
    "Move_SW": {
        "recognition": "DirectHit",
        "action": "PressMultipleKeys",
        "action_param": {
            "keys": ["s", "a", "shift"],
            "duration": 2.0
        },
        "next": ["Circle_Move"]
    },
    
    # 绕圈移动
    "Circle_Move": {
        "next": [
            "Circle_W",
            "Circle_D",
            "Circle_S",
            "Circle_A"
        ]
    },
    
    "Circle_W": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {"direction": "w", "duration": 1.0},
        "next": ["Circle_D"]
    },
    
    "Circle_D": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {"direction": "d", "duration": 1.0},
        "next": ["Circle_S"]
    },
    
    "Circle_S": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {"direction": "s", "duration": 1.0},
        "next": ["Circle_A"]
    },
    
    "Circle_A": {
        "recognition": "DirectHit",
        "action": "RunWithShift",
        "action_param": {"direction": "a", "duration": 1.0}
    }
}

# ========== 保存示例配置到文件 ==========

def save_example(filename, config):
    """保存示例配置到 JSON 文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"[OK] 已保存: {filename}")

if __name__ == "__main__":
    print("=" * 60)
    print("PostMessage 输入功能 - Pipeline 示例")
    print("=" * 60)
    
    # 保存示例配置
    save_example("pipeline_basic_example.json", pipeline_example)
    save_example("pipeline_game_sequence.json", game_sequence_1)
    save_example("pipeline_combat_combo.json", combat_combo)
    save_example("pipeline_complex_movement.json", complex_movement)
    
    print()
    print("=" * 60)
    print("所有示例已保存到当前目录")
    print("=" * 60)
    print()
    print("使用方法：")
    print("1. 将 JSON 配置复制到你的 pipeline.json 文件")
    print("2. 根据实际游戏调整参数（direction、duration 等）")
    print("3. 运行 MaaFramework 任务")
    print()
    print("关键参数说明：")
    print("- direction: 方向键（'w', 'a', 's', 'd'）")
    print("- duration: 持续时长（秒）")
    print("- shift_delay: 按下方向键后多久按 Shift（秒）")
    print("- keys: 按键列表（支持字符、特殊键名称）")
    print()
