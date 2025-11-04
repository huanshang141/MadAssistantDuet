<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img alt="LOGO" src="https://cdn.jsdelivr.net/gh/MaaAssistantArknights/design@main/logo/maa-logo_512x512.png" width="256" height="256" />
</p>

<div align="center">

# MaaPracticeBoilerplate

</div>

二重螺旋小助手，正在锐意开发中，由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！

> MAD指MAD Assistant Duet

## 使用

1. 目前只支持桌面端（非模拟器），且游戏需使用**无边框窗口**运行，通过修改系统分辨率可以降低能耗
2. 前往[release](https://github.com/huanshang141/MdaAssistantDuet/releases)下载对应版本
3. 建议先运行游戏，再运行脚本
4. 解压后，使用管理员权限运行`MFAAvalonia.exe`
5. 可以勾选设置闪避键，默认为左shift键（游戏默认设置）
6. 手动选择游戏窗口，然后直接运行对应任务即可，如果出现问题，先进行截图测试，如果截图失败，在设置-连接设置更改捕获方式和触控模式
7. 不能携带增加移速的mod，推荐使用水母作为主控
8. 游戏须在前台运行，需要后台挂机刷可以参考[后台运行](https://m7a.top/#/assets/docs/Background)
9. 移动逻辑在`resource\pipeline`中，如果遇到卡墙可以手动修改某一步的持续时间，如65级mod中，如果角色偏北，调整`resource\pipeline\扼守\map1.json`，找到
```json
    "def_map1_a3":{
        "recognition": "DirectHit",
        "action": "Custom",
        "custom_action": "RunWithShift",
        "custom_action_param": {
            "direction": "w",     
            "duration": 1,       
            "shift_delay": 0.05  
        },
        "next": ["def_map1_a4"]
    },
```
修改duration后面的数字，指的是移动的时间，单位为秒，如果偏北，减小之

## 鸣谢

本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！
