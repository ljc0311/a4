from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap
import json
import os

class ImageDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        
    def paint(self, painter, option, index):
        if index.column() == 4:  # 主图列
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
                    # 获取主窗口实例：可能是MainWindow直接传入，也可能是通过ShotsWindow的parent_window
                    main_window = None
                    if hasattr(self.parent_widget, 'current_project_name'):
                        # parent_widget 是 MainWindow 实例
                        main_window = self.parent_widget
                    elif hasattr(self.parent_widget, 'parent_window'):
                        # parent_widget 是 ShotsWindow 实例
                        main_window = self.parent_widget.parent_window
                    
                    if main_window and hasattr(main_window, 'current_project_name') and main_window.current_project_name:
                        project_manager = getattr(main_window, 'project_manager', None)
                        if project_manager and not os.path.isabs(image_path):
                            project_root = project_manager.get_project_path(main_window.current_project_name)
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
            super().paint(painter, option, index)
            
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
                    # 获取主窗口实例：可能是MainWindow直接传入，也可能是通过ShotsWindow的parent_window
                    main_window = None
                    if hasattr(self.parent_widget, 'current_project_name'):
                        # parent_widget 是 MainWindow 实例
                        main_window = self.parent_widget
                    elif hasattr(self.parent_widget, 'parent_window'):
                        # parent_widget 是 ShotsWindow 实例
                        main_window = self.parent_widget.parent_window
                    
                    if main_window and hasattr(main_window, 'current_project_name') and main_window.current_project_name:
                        project_manager = getattr(main_window, 'project_manager', None)
                        if project_manager and not os.path.isabs(path):
                            project_root = project_manager.get_project_path(main_window.current_project_name)
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
        from PyQt5.QtCore import QEvent, Qt
        from PyQt5.QtWidgets import QMenu, QAction
        
        if index.column() == 4:  # 图片列 - 点击放大显示
            if event.type() == QEvent.MouseButtonPress:
                image_path = model.data(index, Qt.DisplayRole)
                if image_path and os.path.exists(image_path):
                    # 导入并显示图片查看器对话框
                    from src.gui.image_viewer_dialog import ImageViewerDialog
                    dialog = ImageViewerDialog(image_path, self.parent_widget)
                    dialog.exec_()
                    return True
                    
        elif index.column() == 8:  # 备选图片列 - 处理多图片选择
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
            # 获取主窗口实例：可能是MainWindow直接传入，也可能是通过ShotsWindow的parent_window
            main_window = None
            if hasattr(self.parent_widget, 'on_shots_alternative_image_selected'):
                # parent_widget 是 MainWindow 实例
                main_window = self.parent_widget
            elif hasattr(self.parent_widget, 'parent_window'):
                # parent_widget 是 ShotsWindow 实例
                main_window = self.parent_widget.parent_window
            
            if main_window and hasattr(main_window, 'on_shots_alternative_image_selected'):
                main_window.on_shots_alternative_image_selected(row_index, image_path)
                print(f"已选择备选图片作为主图: {image_path}")
            else:
                print(f"无法访问主窗口或方法不存在，parent_widget类型: {type(self.parent_widget)}")
        except Exception as e:
            print(f"选择备选图片时发生错误: {e}")
            import traceback
            traceback.print_exc()
    
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
                    import os
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
                
                print(f"已从第{row_index+1}行删除图片: {image_path}")
            
        except Exception as e:
            print(f"删除备选图片时发生错误: {e}")

    def sizeHint(self, option, index):
        if index.column() == 4:  # 图片列
            return QSize(150, 100)
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
                    return QSize(300, max(100, height))
            return QSize(300, 100)
        return super().sizeHint(option, index)


class ShotsWindow(QDialog):
    def __init__(self, parent, shots_data):
        # 设置parent为None，让窗口完全独立，避免模态行为
        super().__init__(None)
        self.setWindowTitle("分镜列表")
        self.resize(1200, 800)
        
        # 设置窗口标志，让窗口可以正常切换激活状态，而不是一直保持在前端
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        
        # 保存父窗口引用，以便需要时使用
        self.parent_window = parent

        self.shots_data = shots_data

        self._create_widgets()

    def _create_widgets(self):
        layout = QVBoxLayout()

        self.table_widget = QTableWidget()
        self.table_widget.setFont(QFont("微软雅黑", 13))
        # 表格样式已在CSS文件中定义
        self.table_widget.setToolTip("分镜表格，可编辑和复制内容")
        # self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers) # Make table read-only initially

        # Define columns (删除编号列)
        columns = ('文案', '分镜', '角色', '提示词', '主图', '视频提示词', '音效', '操作', '备选图片')
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)

        # Set column widths (optional, adjust as needed)
        header = self.table_widget.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive) # '文案' column
        header.setSectionResizeMode(1, QHeaderView.Interactive) # '分镜' column
        header.setSectionResizeMode(2, QHeaderView.Interactive) # '角色' column
        header.setSectionResizeMode(3, QHeaderView.Interactive) # '提示词' column
        header.setSectionResizeMode(4, QHeaderView.Interactive) # '图片' column
        header.setSectionResizeMode(5, QHeaderView.Interactive) # '视频提示词' column
        header.setSectionResizeMode(6, QHeaderView.Interactive) # '语音' column
        header.setSectionResizeMode(7, QHeaderView.Interactive) # '操作' column
        header.setSectionResizeMode(8, QHeaderView.Interactive) # '备选图片' column
        header.setStretchLastSection(True) # Stretch the last section

        # Set ImageDelegate for '图片' and '备选图片' columns
        # 传入ShotsWindow实例而不是table_widget，以便访问parent_window
        self.table_widget.setItemDelegateForColumn(4, ImageDelegate(self))
        self.table_widget.setItemDelegateForColumn(8, ImageDelegate(self))

        # Add data
        self.table_widget.setRowCount(len(self.shots_data))
        for i, shot in enumerate(self.shots_data):
            item_description = QTableWidgetItem(shot.get('description', ''))
            item_scene = QTableWidgetItem(shot.get('scene', ''))
            item_role = QTableWidgetItem(shot.get('role', ''))
            item_prompt = QTableWidgetItem(shot.get('prompt', ''))
            # For image columns, we will set the data directly, and the delegate will handle rendering
            image_path = shot.get('image', '')
            alt_images_path = shot.get('alternative_images', '')

            item_video_prompt = QTableWidgetItem(shot.get('video_prompt', ''))
            item_audio = QTableWidgetItem(shot.get('audio', ''))
            # Enable text wrapping and set alignment for relevant columns
            item_description.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            item_description.setFlags(item_description.flags() | Qt.TextWordWrap)

            item_scene.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            item_scene.setFlags(item_scene.flags() | Qt.TextWordWrap)

            item_role.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            item_role.setFlags(item_role.flags() | Qt.TextWordWrap)

            item_prompt.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            item_prompt.setFlags(item_prompt.flags() | Qt.TextWordWrap)

            self.table_widget.setItem(i, 0, item_description)
            self.table_widget.setItem(i, 1, item_scene)
            self.table_widget.setItem(i, 2, item_role)
            self.table_widget.setItem(i, 3, item_prompt)
            self.table_widget.setItem(i, 4, QTableWidgetItem(image_path)) # Set image path as item data
            self.table_widget.setItem(i, 5, item_video_prompt)
            self.table_widget.setItem(i, 6, item_audio)
            
            # 创建操作按钮组件
            operation_widget = self.create_operation_buttons(i)
            self.table_widget.setCellWidget(i, 7, operation_widget)
            
            self.table_widget.setItem(i, 8, QTableWidgetItem(alt_images_path)) # Set alternative images path as item data

        # Adjust row heights to fit content after wrapping
        # Ensure that image columns have enough height
        for i in range(self.table_widget.rowCount()):
            self.table_widget.setRowHeight(i, max(self.table_widget.rowHeight(i), 100)) # Minimum height for image rows
        self.table_widget.resizeRowsToContents()

        layout.addWidget(self.table_widget)
        self.setLayout(layout)

    def get_prompt_for_row(self, row):
        """获取指定行"提示词"列的内容"""
        if 0 <= row < self.table_widget.rowCount():
            item = self.table_widget.item(row, 3) # 索引3是"提示词"列
            if item:
                return item.text()
        return ""
    
    def create_operation_buttons(self, row_index):
        """为指定行创建操作按钮组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # 绘图按钮
        draw_btn = QPushButton("绘图")
        draw_btn.setProperty("class", "draw-button")
        draw_btn.clicked.connect(lambda: self.handle_draw_btn(row_index))
        layout.addWidget(draw_btn)
        
        # 配音按钮
        voice_btn = QPushButton("配音")
        voice_btn.setProperty("class", "voice-button")
        voice_btn.clicked.connect(lambda: self.handle_voice_btn(row_index))
        layout.addWidget(voice_btn)
        
        # 分镜设置按钮
        setting_btn = QPushButton("设置")
        setting_btn.setProperty("class", "setting-button")
        setting_btn.clicked.connect(lambda: self.handle_shot_setting_btn(row_index))
        layout.addWidget(setting_btn)
        
        widget.setLayout(layout)
        return widget
    
    def handle_draw_btn(self, row_index):
        """处理绘图按钮点击事件"""
        try:
            # 获取提示词
            prompt = self.get_prompt_for_row(row_index)
            if not prompt:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", f"第{row_index+1}行没有提示词内容")
                return
            
            # 获取主窗口实例
            main_window = None
            if self.parent_window and hasattr(self.parent_window, 'parent_window'):
                main_window = self.parent_window.parent_window
            
            # 调用主窗口的绘图处理方法
            if main_window and hasattr(main_window, 'process_draw_request'):
                # 显示进度提示
                if hasattr(self.parent_window, 'show_progress'):
                    self.parent_window.show_progress(f"正在为第{row_index+1}行生成图片...")
                
                # 调用主窗口的绘图处理方法
                main_window.process_draw_request(row_index, prompt)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", "无法找到主窗口的绘图处理方法")
                
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"绘图功能出错: {str(e)}")
    
    def handle_voice_btn(self, row_index):
        """处理配音按钮点击事件"""
        try:
            # 获取当前行的文案内容
            text_item = self.table_widget.item(row_index, 0)  # 文案列
            if not text_item or not text_item.text().strip():
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", "当前分镜没有文案内容，无法进行配音")
                return
            
            text_content = text_item.text().strip()
            
            # 导入AI配音对话框
            from src.gui.ai_voice_dialog import AIVoiceDialog
            
            # 创建并显示AI配音对话框
            dialog = AIVoiceDialog(self, text_content, row_index)
            if dialog.exec_() == QDialog.Accepted:
                # 用户确认生成，获取生成结果
                result = dialog.get_generation_result()
                if result and result.get('success'):
                    # 更新表格中的语音列信息
                    voice_item = self.table_widget.item(row_index, 6)  # 语音列
                    if voice_item:
                        voice_item.setText(f"已生成: {os.path.basename(result['audio_file'])}")
                    else:
                        voice_item = QTableWidgetItem(f"已生成: {os.path.basename(result['audio_file'])}")
                        self.table_widget.setItem(row_index, 6, voice_item)
                    
                    # 更新分镜数据中的语音文件路径
                    if hasattr(self.parent_window, 'shots_data') and self.parent_window.shots_data and row_index < len(self.parent_window.shots_data):
                        self.parent_window.shots_data[row_index]['voice_file'] = result['audio_file']
                        # 自动保存项目
                        self.parent_window.save_current_project()
                        logger.info(f"已更新第{row_index+1}行分镜的语音文件: {result['audio_file']}")
                    
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "成功", "语音生成完成！")
                elif result:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "错误", f"语音生成失败: {result.get('error', '未知错误')}")
                    
        except ImportError as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"无法加载AI配音模块: {str(e)}")
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"配音功能出错: {str(e)}")
    
    def handle_shot_setting_btn(self, row_index):
        """处理分镜设置按钮点击事件"""
        try:
            # 如果有父窗口，调用父窗口的分镜设置处理方法
            if self.parent_window and hasattr(self.parent_window, 'handle_shot_setting_btn'):
                self.parent_window.handle_shot_setting_btn(row_index)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", f"分镜设置功能 - 第{row_index+1}行\n\n此功能正在开发中，敬请期待！")
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"分镜设置功能出错: {str(e)}")

    def update_shot_image(self, row_index, image_path):
        """更新指定行的图片"""
        try:
            if 0 <= row_index < self.table_widget.rowCount():
                # 获取当前备选图片列的内容
                alt_image_item = self.table_widget.item(row_index, 8)
                current_alt_images = alt_image_item.text() if alt_image_item else ""
                
                # 将新图片追加到备选图片列表中（与main_window.py保持一致使用逗号分隔）
                if current_alt_images and current_alt_images.strip():
                    # 检查图片是否已存在，统一使用逗号分隔符
                    existing_paths = [p.strip() for p in current_alt_images.split(',') if p.strip()]
                    if image_path not in existing_paths:
                        new_alt_images = current_alt_images + "," + image_path
                        print(f"将新图片追加到备选图片列表: {image_path}")
                    else:
                        new_alt_images = current_alt_images
                        print(f"图片已存在于备选图片列表中: {image_path}")
                else:
                    new_alt_images = image_path
                    print(f"设置第一个备选图片: {image_path}")
                
                # 更新备选图片列（索引8）
                alt_image_item = QTableWidgetItem(new_alt_images)
                alt_image_item.setToolTip(f"备选图片路径: {new_alt_images}")
                self.table_widget.setItem(row_index, 8, alt_image_item)
                
                # 如果图片列（索引4）为空，则设置为第一张图片
                main_image_item = self.table_widget.item(row_index, 4)
                if not main_image_item or not main_image_item.text().strip():
                    image_item = QTableWidgetItem(image_path)
                    image_item.setToolTip(f"图片路径: {image_path}")
                    self.table_widget.setItem(row_index, 4, image_item)
                
                # 强制刷新表格显示
                self.table_widget.viewport().update()
                
                print(f"已更新第{row_index+1}行的图片: {image_path}")
                return True
            else:
                print(f"行索引{row_index}超出范围")
                return False
        except Exception as e:
            print(f"更新图片时发生错误: {e}")
            return False
    
    def on_alternative_image_selected(self, row_index, selected_image_path):
        """处理备选图片被选中的事件"""
        try:
            if 0 <= row_index < self.table_widget.rowCount():
                # 将选中的图片设置为主图
                image_item = QTableWidgetItem(selected_image_path)
                image_item.setToolTip(f"图片路径: {selected_image_path}")
                self.table_widget.setItem(row_index, 4, image_item)
                
                # 强制刷新表格显示
                self.table_widget.viewport().update()
                
                print(f"第{row_index+1}行已选择图片: {selected_image_path}")
                
                # 可以在这里添加其他逻辑，比如通知父窗口图片已更改
                if hasattr(self.parent_window, 'on_shot_image_changed'):
                    self.parent_window.on_shot_image_changed(row_index, selected_image_path)
                    
        except Exception as e:
            print(f"选择备选图片时发生错误: {e}")

# 注释掉独立启动代码，避免与main.py冲突
# if __name__ == '__main__':
#     import sys
#     from PyQt5.QtWidgets import QApplication
# 
#     app = QApplication(sys.argv)
# 
#     # Sample data structure based on previous parsing logic
#     sample_shots_data = [
#         {'description': '前些年，鬼吹灯、盗墓笔记、黄金瞳等影视剧风靡一时，如今喧嚣散尽，狗粮来无事，便想将这行当里的见闻付诸笔端', 'scene': '场景1', 'characters': []},
#         {'description': '云顶天宫、秦岭神树，我虽未曾亲见，黄金瞳更是遥不可及，但自十六岁踏入古董行起，那些常人难解的奇事，我却亲眼得见', 'scene': '场景2', 'characters': []},
#         {'description': '故事，便要从头说起.我生于东北边陲的小山村，紧邻莫河，那儿的冬天，寒风能将人冻僵', 'scene': '场景3', 'characters': []},
#     ]
# 
#     shots_window = ShotsWindow(None, sample_shots_data)
#     shots_window.show()
#     sys.exit(app.exec_())