# -*- mode: python ; coding: utf-8 -*-
"""
MaaAgent PyInstaller 配置文件
用于打包 Python Agent 为单可执行文件

使用方法:
    cd 到项目根目录，然后执行:
    pyinstaller tools/MaaAgent.spec
"""

import os
import sys

# 获取项目根目录(spec 文件在 tools/ 下,需要返回上一级)
spec_root = os.path.dirname(os.path.abspath(SPECPATH))

block_cipher = None

# Try to collect maa package non-python data (native libs, bin, etc.) so
# the bundled app can find maa/bin at runtime inside the _MEI tempdir.
datas_list = []
try:
    import maa
    maa_dir = os.path.dirname(os.path.abspath(maa.__file__))

    # Walk maa package directory and include non-.py files (binaries/resources)
    for root, dirs, files in os.walk(maa_dir):
        for fname in files:
            # include everything that's not a python source file; keep extensions that matter
            if not fname.endswith('.py') and not fname.endswith('.pyc') and not fname.endswith('.pyo'):
                src = os.path.join(root, fname)
                rel = os.path.relpath(root, maa_dir)
                # destination inside bundle should preserve package structure
                dest = os.path.join('maa', rel) if rel != '.' else 'maa'
                datas_list.append((src, dest))
except Exception:
    # If maa isn't importable at spec build time, leave datas_list empty.
    datas_list = []

# Also include agent/postmessage/actionJSON directory (pipeline action JSONs)
# NOTE: actionJSON files should NOT be bundled into the exe; they will be
# read from the working directory at runtime (e.g. <working_dir>\agent\actionJSON).
# The previous implementation added agent/postmessage/actionJSON into datas_list,
# which caused JSON files to be embedded into the frozen _MEI tempdir. That is
# undesirable for runtime resource management and editing. Intentionally left
# no datas added for actionJSON here.


a = Analysis(
    [os.path.join(spec_root, 'agent', 'main.py')],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MaaAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口以显示日志
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可选: 添加图标文件路径
)
