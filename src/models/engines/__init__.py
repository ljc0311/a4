# -*- coding: utf-8 -*-
"""
图像生成引擎实现模块
包含各种图像生成服务的具体实现
"""

# 导入所有引擎实现
try:
    from .pollinations_engine import PollinationsEngine
except ImportError:
    PollinationsEngine = None

try:
    from .comfyui_engine import ComfyUILocalEngine, ComfyUICloudEngine
except ImportError:
    ComfyUILocalEngine = None
    ComfyUICloudEngine = None

try:
    from .dalle_engine import DalleEngine
except ImportError:
    DalleEngine = None

try:
    from .stability_engine import StabilityEngine
except ImportError:
    StabilityEngine = None

try:
    from .imagen_engine import ImagenEngine
except ImportError:
    ImagenEngine = None

try:
    from .cogview_3_flash_engine import CogView3FlashEngine
except ImportError:
    CogView3FlashEngine = None

__all__ = [
    'PollinationsEngine',
    'ComfyUILocalEngine',
    'ComfyUICloudEngine',
    'DalleEngine',
    'StabilityEngine',
    'ImagenEngine',
    'CogView3FlashEngine'
]