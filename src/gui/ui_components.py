# -*- coding: utf-8 -*-
"""
UI组件模块
包含可重用的UI组件类
"""

import os
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from src.utils.logger import logger


class ImageDelegate(QStyledItemDelegate):
    """图片代理类，用于在表格中显示图片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
    
    def paint(self, painter, option, index):
        if index.column() == 4:  # 主图列
            # 首先检查是否有DecorationRole数据（来自storyboard_tab的setData调用）
            decoration_data = index.model().data(index, Qt.DecorationRole)
            if decoration_data and isinstance(decoration_data, QPixmap):
                # 直接使用已经缩放好的pixmap
                scaled_pixmap = decoration_data.scaled(option.rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
                y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
                return
            
            # 如果没有DecorationRole数据，则处理DisplayRole数据（文本路径）
            image_path = index.model().data(index, Qt.DisplayRole)
            if image_path:
                # 首先检查原始路径
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(option.rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
                        y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
                        painter.drawPixmap(x, y, scaled_pixmap)
                        return
                else:
                    # 尝试修复相对路径问题
                    if hasattr(self.parent_widget, 'current_project_name') and self.parent_widget.current_project_name:
                        project_manager = getattr(self.parent_widget, 'project_manager', None)
                        if project_manager and not os.path.isabs(image_path):
                            project_root = project_manager.get_project_path(self.parent_widget.current_project_name)
                            absolute_path = os.path.join(project_root, image_path)
                            if os.path.exists(absolute_path):
                                pixmap = QPixmap(absolute_path)
                                if not pixmap.isNull():
                                    scaled_pixmap = pixmap.scaled(option.rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                    x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
                                    y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
                                    painter.drawPixmap(x, y, scaled_pixmap)
                                    # 更新模型中的数据为绝对路径
                                    try:
                                        index.model().setData(index, absolute_path, Qt.DisplayRole)
                                    except:
                                        pass  # 忽略更新失败
                                    return
            # 如果没有有效的图片数据，不绘制任何内容（避免显示文本）
            return
            
        elif index.column() == 8:  # 备选图片列
            image_data = index.model().data(index, Qt.DisplayRole)
            if not image_data:
                super().paint(painter, option, index)
                return
                
            # 获取所有有效图片路径
            image_paths = []
            # 统一使用逗号分隔符，与main_window.py保持一致
            for path in image_data.split(','):
                path = path.strip()
                if not path:
                    continue
                    
                if os.path.exists(path):
                    image_paths.append(path)
                else:
                    # 尝试修复相对路径问题
                    if hasattr(self.parent_widget, 'current_project_name') and self.parent_widget.current_project_name:
                        project_manager = getattr(self.parent_widget, 'project_manager', None)
                        if project_manager and not os.path.isabs(path):
                            project_root = project_manager.get_project_path(self.parent_widget.current_project_name)
                            absolute_path = os.path.join(project_root, path)
                            if os.path.exists(absolute_path):
                                image_paths.append(absolute_path)
                                # 更新模型中的数据
                                try:
                                    current_data = image_data.replace(path, absolute_path)
                                    index.model().setData(index, current_data, Qt.DisplayRole)
                                except:
                                    pass  # 忽略更新失败
            
            if not image_paths:
                super().paint(painter, option, index)
                return
                
            # 计算多行布局参数
            max_cols = 5  # 每行最多5张图片
            spacing = 5
            available_width = option.rect.width() - spacing * 2  # 留出左右边距
            thumb_size = min(available_width // max_cols - spacing, 120)  # 限制最大尺寸为120
            
            # 计算实际每行图片数量和布局
            cols_per_row = min(len(image_paths), max_cols)
            rows = (len(image_paths) + max_cols - 1) // max_cols  # 向上取整
            
            # 计算起始位置
            total_width = cols_per_row * thumb_size + (cols_per_row - 1) * spacing
            x_start = option.rect.x() + (option.rect.width() - total_width) // 2
            total_height = rows * thumb_size + (rows - 1) * spacing
            y_start = option.rect.y() + (option.rect.height() - total_height) // 2
            
            # 绘制所有备选图片缩略图（多行布局）
            for i, path in enumerate(image_paths):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    thumb = pixmap.scaled(thumb_size, thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    # 计算当前图片的行列位置
                    row = i // max_cols
                    col = i % max_cols
                    
                    # 计算当前行的图片数量，用于居中对齐
                    current_row_count = min(max_cols, len(image_paths) - row * max_cols)
                    current_row_width = current_row_count * thumb_size + (current_row_count - 1) * spacing
                    current_x_start = option.rect.x() + (option.rect.width() - current_row_width) // 2
                    
                    x = current_x_start + col * (thumb_size + spacing)
                    y = y_start + row * (thumb_size + spacing)
                    
                    # 居中绘制缩略图
                    thumb_x = x + (thumb_size - thumb.width()) // 2
                    thumb_y = y + (thumb_size - thumb.height()) // 2
                    painter.drawPixmap(thumb_x, thumb_y, thumb)
        else:
            super().paint(painter, option, index)
    
    def editorEvent(self, event, model, option, index):
        """处理编辑事件"""
        if index.column() == 4:  # 图片列 - 点击放大显示
            from PyQt5.QtCore import QEvent, Qt
            from PyQt5.QtWidgets import QApplication
            
            if event.type() == QEvent.MouseButtonPress:
                image_path = model.data(index, Qt.DisplayRole)
                if image_path and os.path.exists(image_path):
                    # 导入并显示图片查看器对话框
                    from src.gui.image_viewer_dialog import ImageViewerDialog
                    dialog = ImageViewerDialog(image_path, self.parent_widget)
                    dialog.exec_()
                    return True
                    
        elif index.column() == 8:  # 备选图片列
            from PyQt5.QtCore import QEvent, Qt
            from PyQt5.QtWidgets import QApplication, QMenu, QAction
            
            if event.type() == QEvent.MouseButtonPress:
                image_data = model.data(index, Qt.DisplayRole)
                if not image_data:
                    return super().editorEvent(event, model, option, index)
                
                # 获取所有有效图片路径
                image_paths = []
                # 统一使用逗号分隔符，与main_window.py保持一致
                for path in image_data.split(','):
                    path = path.strip()
                    if path and os.path.exists(path):
                        image_paths.append(path)
                
                if not image_paths:
                    return super().editorEvent(event, model, option, index)
                
                # 计算点击位置对应的图片
                max_cols = 5
                spacing = 5
                available_width = option.rect.width() - spacing * 2
                thumb_size = min(available_width // max_cols - spacing, 120)
                
                cols_per_row = min(len(image_paths), max_cols)
                rows = (len(image_paths) + max_cols - 1) // max_cols
                
                total_width = cols_per_row * thumb_size + (cols_per_row - 1) * spacing
                x_start = option.rect.x() + (option.rect.width() - total_width) // 2
                total_height = rows * thumb_size + (rows - 1) * spacing
                y_start = option.rect.y() + (option.rect.height() - total_height) // 2
                
                # 检查点击位置
                click_x = event.pos().x()
                click_y = event.pos().y()
                
                for i, path in enumerate(image_paths):
                    row = i // max_cols
                    col = i % max_cols
                    
                    current_row_count = min(max_cols, len(image_paths) - row * max_cols)
                    current_row_width = current_row_count * thumb_size + (current_row_count - 1) * spacing
                    current_x_start = option.rect.x() + (option.rect.width() - current_row_width) // 2
                    
                    x = current_x_start + col * (thumb_size + spacing)
                    y = y_start + row * (thumb_size + spacing)
                    
                    if (x <= click_x <= x + thumb_size and y <= click_y <= y + thumb_size):
                        # 检查是否为右键点击
                        if event.button() == Qt.RightButton:
                            # 显示右键菜单
                            menu = QMenu(self.parent_widget)
                            
                            # 添加"选中图片"选项
                            select_action = QAction("选中图片", menu)
                            select_action.triggered.connect(lambda: self._select_alternative_image(index.row(), path))
                            menu.addAction(select_action)
                            
                            # 添加"删除图片"选项
                            delete_action = QAction("删除图片", menu)
                            delete_action.triggered.connect(lambda: self._delete_alternative_image(index, path, i))
                            menu.addAction(delete_action)
                            
                            # 在鼠标位置显示菜单
                            global_pos = self.parent_widget.mapToGlobal(event.pos())
                            menu.exec_(global_pos)
                            return True
                        
                        elif event.button() == Qt.LeftButton:
                            # 左键点击 - 放大显示图片
                            from src.gui.image_viewer_dialog import ImageViewerDialog
                            dialog = ImageViewerDialog(path, self.parent_widget)
                            dialog.exec_()
                            return True
                
                return super().editorEvent(event, model, option, index)
        
        return super().editorEvent(event, model, option, index)
    
    def _select_alternative_image(self, row_index, image_path):
        """选中备选图片作为主图"""
        try:
            # 直接调用本类的on_alternative_image_selected方法
            self.on_alternative_image_selected(row_index, image_path)
        except Exception as e:
            print(f"选择备选图片时发生错误: {e}")
    
    def on_alternative_image_selected(self, row_index, selected_image_path):
        """处理备选图片被选中的事件"""
        try:
            if hasattr(self.parent_widget, 'table_widget'):
                table_widget = self.parent_widget.table_widget
                if 0 <= row_index < table_widget.rowCount():
                    # 将选中的图片设置为主图
                    from PyQt5.QtWidgets import QTableWidgetItem
                    image_item = QTableWidgetItem(selected_image_path)
                    image_item.setToolTip(f"图片路径: {selected_image_path}")
                    table_widget.setItem(row_index, 4, image_item)
                    
                    # 强制刷新表格显示
                    table_widget.viewport().update()
                    
                    print(f"第{row_index+1}行已选择图片: {selected_image_path}")
                    
        except Exception as e:
            print(f"选择备选图片时发生错误: {e}")
    
    def _delete_alternative_image(self, index, image_path, image_index):
        """从备选图片列表中删除指定图片"""
        try:
            model = index.model()
            current_data = model.data(index, Qt.DisplayRole)
            if not current_data:
                return
            
            row_index = index.row()
            
            # 获取当前所有图片路径
            # 统一使用逗号分隔符，与main_window.py保持一致
            image_paths = [p.strip() for p in current_data.split(',') if p.strip()]
            
            # 移除指定的图片路径
            if image_path in image_paths:
                image_paths.remove(image_path)
                
                # 更新单元格数据
                # 统一使用逗号分隔符，与main_window.py保持一致
                new_data = ','.join(image_paths) if image_paths else ''
                model.setData(index, new_data, Qt.DisplayRole)
                
                # 更新底层数据 - shots_data
                if hasattr(self.parent_widget, 'shots_data') and self.parent_widget.shots_data and row_index < len(self.parent_widget.shots_data):
                    self.parent_widget.shots_data[row_index]['alternative_images'] = new_data
                    print(f"已更新第{row_index+1}行shots_data备选图片路径")
                    
                    # 自动保存项目
                    if hasattr(self.parent_widget, 'current_project_name') and self.parent_widget.current_project_name:
                        try:
                            self.parent_widget.save_current_project()
                            print(f"删除备选图片后自动保存项目: {self.parent_widget.current_project_name}")
                        except Exception as save_error:
                            print(f"自动保存项目失败: {save_error}")
                
                # 删除实际图片文件
                try:
                    # 构建完整的文件路径
                    if hasattr(self.parent_widget, 'current_project_dir') and self.parent_widget.current_project_dir:
                        if os.path.isabs(image_path):
                            full_image_path = image_path
                        else:
                            full_image_path = os.path.join(self.parent_widget.current_project_dir, image_path)
                        
                        if os.path.exists(full_image_path):
                            os.remove(full_image_path)
                            print(f"已删除图片文件: {full_image_path}")
                        else:
                            print(f"图片文件不存在，跳过删除: {full_image_path}")
                    else:
                        print("无法确定项目目录，跳过文件删除")
                except Exception as file_error:
                    print(f"删除图片文件时发生错误: {file_error}")
                
                # 强制刷新表格显示
                if hasattr(self.parent_widget, 'table_widget'):
                    self.parent_widget.table_widget.viewport().update()
                elif hasattr(self.parent_widget, 'shots_settings_table'):
                    self.parent_widget.shots_settings_table.viewport().update()
                
                print(f"已从第{row_index+1}行删除图片: {image_path}")
            
        except Exception as e:
            print(f"删除备选图片时发生错误: {e}")
    
    def sizeHint(self, option, index):
        """返回单元格大小提示"""
        if index.column() == 4:  # 图片列
            return option.rect.size()
        elif index.column() == 8:  # 备选图片列
            # 根据图片数量计算所需高度
            image_data = index.model().data(index, Qt.DisplayRole)
            if image_data:
                # 统一使用逗号分隔符，与main_window.py保持一致
                image_count = len([p for p in image_data.split(',') if p.strip()])
                if image_count > 0:
                    max_cols = 5
                    rows = (image_count + max_cols - 1) // max_cols
                    thumb_size = 120
                    spacing = 5
                    height = rows * thumb_size + (rows - 1) * spacing + 20  # 额外边距
                    return option.rect.size().expandedTo(option.rect.size().expandedTo(option.rect.size()).expandedTo(option.rect.size()))
        return super().sizeHint(option, index)


class CustomWebEnginePage(QWebEnginePage):
    """自定义Web引擎页面，用于处理ComfyUI Web界面"""
    
    def __init__(self, parent=None, on_console_message=None):
        super().__init__(parent)
        self.on_console_message = on_console_message
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """处理JavaScript控制台消息"""
        if self.on_console_message:
            self.on_console_message(level, message, lineNumber, sourceID)
        else:
            logger.debug(f"JS Console [{level}]: {message} (Line: {lineNumber}, Source: {sourceID})")