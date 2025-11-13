"""
Deprecated: This module has been removed.

All key input is now handled by Maa controller APIs (post_key_down/up/click_key).
This file remains only to avoid import errors. Importing from here is unsupported.
"""

raise ImportError(
    "PostMessageInputHelper has been removed. Use Maa controller APIs via context.tasker.controller."
)
