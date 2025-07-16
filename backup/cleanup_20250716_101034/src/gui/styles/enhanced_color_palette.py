#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的现代化配色方案
基于Material Design 3.0和现代UI趋势设计
支持多种主题模式和自定义配色
"""

from typing import Dict, List, Tuple
from enum import Enum
import colorsys


class ColorScheme(Enum):
    """配色方案类型"""
    MATERIAL = "material"
    FLUENT = "fluent"
    MACOS = "macos"
    CUSTOM = "custom"


class EnhancedColorPalette:
    """增强的配色方案"""
    
    @staticmethod
    def get_modern_light_colors() -> Dict[str, str]:
        """现代化浅色主题 - 基于Material Design 3.0"""
        return {
            # === 主色系 ===
            "primary": "#6750A4",           # 紫色主色
            "primary_container": "#EADDFF", # 主色容器
            "on_primary": "#FFFFFF",        # 主色上的文字
            "on_primary_container": "#21005D", # 主色容器上的文字
            
            # === 次要色系 ===
            "secondary": "#625B71",         # 次要色
            "secondary_container": "#E8DEF8", # 次要色容器
            "on_secondary": "#FFFFFF",      # 次要色上的文字
            "on_secondary_container": "#1D192B", # 次要色容器上的文字
            
            # === 第三色系 ===
            "tertiary": "#7D5260",          # 第三色
            "tertiary_container": "#FFD8E4", # 第三色容器
            "on_tertiary": "#FFFFFF",       # 第三色上的文字
            "on_tertiary_container": "#31111D", # 第三色容器上的文字
            
            # === 表面色系 ===
            "surface": "#FFFBFE",           # 表面色
            "surface_dim": "#DDD8DD",       # 暗表面色
            "surface_bright": "#FFFBFE",    # 亮表面色
            "surface_container_lowest": "#FFFFFF", # 最低容器
            "surface_container_low": "#F7F2FA",    # 低容器
            "surface_container": "#F1ECF4",        # 标准容器
            "surface_container_high": "#ECE6F0",   # 高容器
            "surface_container_highest": "#E6E0E9", # 最高容器
            "surface_variant": "#E7E0EC",   # 表面变体
            "on_surface": "#1C1B1F",        # 表面上的文字
            "on_surface_variant": "#49454F", # 表面变体上的文字
            
            # === 背景色系 ===
            "background": "#FFFBFE",        # 背景色
            "on_background": "#1C1B1F",     # 背景上的文字
            
            # === 轮廓色 ===
            "outline": "#79747E",           # 轮廓色
            "outline_variant": "#CAC4D0",   # 轮廓变体
            
            # === 状态色 ===
            "success": "#00C853",           # 成功色
            "success_container": "#E8F5E8", # 成功容器
            "on_success": "#FFFFFF",        # 成功色上的文字
            "on_success_container": "#1B5E20", # 成功容器上的文字
            
            "warning": "#FF8F00",           # 警告色
            "warning_container": "#FFF3E0", # 警告容器
            "on_warning": "#FFFFFF",        # 警告色上的文字
            "on_warning_container": "#E65100", # 警告容器上的文字
            
            "error": "#BA1A1A",             # 错误色
            "error_container": "#FFDAD6",   # 错误容器
            "on_error": "#FFFFFF",          # 错误色上的文字
            "on_error_container": "#410002", # 错误容器上的文字
            
            "info": "#0277BD",              # 信息色
            "info_container": "#E1F5FE",    # 信息容器
            "on_info": "#FFFFFF",           # 信息色上的文字
            "on_info_container": "#01579B", # 信息容器上的文字
            
            # === 特殊色 ===
            "shadow": "#000000",            # 阴影色
            "scrim": "#000000",             # 遮罩色
            "inverse_surface": "#313033",   # 反转表面
            "inverse_on_surface": "#F4EFF4", # 反转表面上的文字
            "inverse_primary": "#D0BCFF",   # 反转主色
            
            # === 渐变色 ===
            "gradient_primary": "linear-gradient(135deg, #6750A4 0%, #7C4DFF 100%)",
            "gradient_secondary": "linear-gradient(135deg, #625B71 0%, #9C27B0 100%)",
            "gradient_surface": "linear-gradient(180deg, #FFFBFE 0%, #F7F2FA 100%)",
            
            # === 透明度变体 ===
            "primary_alpha_12": "rgba(103, 80, 164, 0.12)",
            "primary_alpha_16": "rgba(103, 80, 164, 0.16)",
            "primary_alpha_24": "rgba(103, 80, 164, 0.24)",
            "surface_alpha_08": "rgba(255, 251, 254, 0.08)",
            "surface_alpha_12": "rgba(255, 251, 254, 0.12)",
        }
    
    @staticmethod
    def get_modern_dark_colors() -> Dict[str, str]:
        """现代化深色主题"""
        return {
            # === 主色系 ===
            "primary": "#D0BCFF",           # 紫色主色
            "primary_container": "#4F378B", # 主色容器
            "on_primary": "#371E73",        # 主色上的文字
            "on_primary_container": "#EADDFF", # 主色容器上的文字
            
            # === 次要色系 ===
            "secondary": "#CCC2DC",         # 次要色
            "secondary_container": "#4A4458", # 次要色容器
            "on_secondary": "#332D41",      # 次要色上的文字
            "on_secondary_container": "#E8DEF8", # 次要色容器上的文字
            
            # === 第三色系 ===
            "tertiary": "#EFB8C8",          # 第三色
            "tertiary_container": "#633B48", # 第三色容器
            "on_tertiary": "#492532",       # 第三色上的文字
            "on_tertiary_container": "#FFD8E4", # 第三色容器上的文字
            
            # === 表面色系 ===
            "surface": "#10131C",           # 表面色
            "surface_dim": "#10131C",       # 暗表面色
            "surface_bright": "#383B4A",    # 亮表面色
            "surface_container_lowest": "#0B0E17", # 最低容器
            "surface_container_low": "#1D1B20",    # 低容器
            "surface_container": "#211F26",        # 标准容器
            "surface_container_high": "#2B2930",   # 高容器
            "surface_container_highest": "#36343B", # 最高容器
            "surface_variant": "#49454F",   # 表面变体
            "on_surface": "#E6E0E9",        # 表面上的文字
            "on_surface_variant": "#CAC4D0", # 表面变体上的文字
            
            # === 背景色系 ===
            "background": "#10131C",        # 背景色
            "on_background": "#E6E0E9",     # 背景上的文字
            
            # === 轮廓色 ===
            "outline": "#938F99",           # 轮廓色
            "outline_variant": "#49454F",   # 轮廓变体
            
            # === 状态色 ===
            "success": "#4CAF50",           # 成功色
            "success_container": "#1B5E20", # 成功容器
            "on_success": "#FFFFFF",        # 成功色上的文字
            "on_success_container": "#C8E6C9", # 成功容器上的文字
            
            "warning": "#FFB74D",           # 警告色
            "warning_container": "#E65100", # 警告容器
            "on_warning": "#000000",        # 警告色上的文字
            "on_warning_container": "#FFE0B2", # 警告容器上的文字
            
            "error": "#FFB4AB",             # 错误色
            "error_container": "#93000A",   # 错误容器
            "on_error": "#690005",          # 错误色上的文字
            "on_error_container": "#FFDAD6", # 错误容器上的文字
            
            "info": "#81D4FA",              # 信息色
            "info_container": "#01579B",    # 信息容器
            "on_info": "#000000",           # 信息色上的文字
            "on_info_container": "#B3E5FC", # 信息容器上的文字
            
            # === 特殊色 ===
            "shadow": "#000000",            # 阴影色
            "scrim": "#000000",             # 遮罩色
            "inverse_surface": "#E6E0E9",   # 反转表面
            "inverse_on_surface": "#313033", # 反转表面上的文字
            "inverse_primary": "#6750A4",   # 反转主色
            
            # === 渐变色 ===
            "gradient_primary": "linear-gradient(135deg, #D0BCFF 0%, #BB86FC 100%)",
            "gradient_secondary": "linear-gradient(135deg, #CCC2DC 0%, #CE93D8 100%)",
            "gradient_surface": "linear-gradient(180deg, #10131C 0%, #1D1B20 100%)",
            
            # === 透明度变体 ===
            "primary_alpha_12": "rgba(208, 188, 255, 0.12)",
            "primary_alpha_16": "rgba(208, 188, 255, 0.16)",
            "primary_alpha_24": "rgba(208, 188, 255, 0.24)",
            "surface_alpha_08": "rgba(16, 19, 28, 0.08)",
            "surface_alpha_12": "rgba(16, 19, 28, 0.12)",
        }
    
    @staticmethod
    def generate_color_variants(base_color: str, steps: int = 5) -> List[str]:
        """生成颜色变体"""
        # 将十六进制颜色转换为RGB
        base_color = base_color.lstrip('#')
        r, g, b = tuple(int(base_color[i:i+2], 16) for i in (0, 2, 4))
        
        # 转换为HSV
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        variants = []
        for i in range(steps):
            # 调整亮度
            new_v = max(0.1, min(1.0, v + (i - steps//2) * 0.15))
            new_r, new_g, new_b = colorsys.hsv_to_rgb(h, s, new_v)
            
            # 转换回十六进制
            hex_color = "#{:02x}{:02x}{:02x}".format(
                int(new_r * 255), int(new_g * 255), int(new_b * 255)
            )
            variants.append(hex_color)
        
        return variants
    
    @staticmethod
    def get_fluent_design_colors() -> Dict[str, str]:
        """Fluent Design风格配色"""
        return {
            "primary": "#0078D4",
            "primary_container": "#E3F2FD",
            "secondary": "#605E5C",
            "surface": "#FAFAFA",
            "background": "#F3F2F1",
            "on_surface": "#323130",
            "outline": "#8A8886",
            "success": "#107C10",
            "warning": "#FF8C00",
            "error": "#D13438",
            "info": "#0078D4",
        }
    
    @staticmethod
    def get_macos_style_colors() -> Dict[str, str]:
        """macOS风格配色"""
        return {
            "primary": "#007AFF",
            "primary_container": "#E3F2FD",
            "secondary": "#5856D6",
            "surface": "#FFFFFF",
            "background": "#F2F2F7",
            "on_surface": "#000000",
            "outline": "#C7C7CC",
            "success": "#34C759",
            "warning": "#FF9500",
            "error": "#FF3B30",
            "info": "#007AFF",
        }
