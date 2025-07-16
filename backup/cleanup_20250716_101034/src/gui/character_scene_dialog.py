import sys
import os
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QTextEdit, QLineEdit, QComboBox, QGroupBox, QFormLayout,
    QMessageBox, QHeaderView, QSplitter, QFrame, QScrollArea,
    QCheckBox, QSpinBox, QProgressDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon
from src.utils.logger import logger
from src.utils.color_optimizer import ColorOptimizer
from src.utils.character_scene_sync import notify_character_changed, notify_scene_changed


class ExtractionThread(QThread):
    """角色场景提取线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, character_scene_manager, text):
        super().__init__()
        self.character_scene_manager = character_scene_manager
        self.text = text
        self._is_cancelled = False

    def run(self):
        """在后台线程中执行提取"""
        try:
            if self._is_cancelled:
                return

            result = self.character_scene_manager.auto_extract_and_save(self.text)

            if not self._is_cancelled:
                self.finished.emit(result)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))

    def cancel(self):
        """取消提取"""
        self._is_cancelled = True


class CharacterSceneDialog(QDialog):
    """角色场景设置对话框"""
    
    # 信号定义
    character_updated = pyqtSignal(str, dict)  # 角色更新信号
    scene_updated = pyqtSignal(str, dict)      # 场景更新信号
    consistency_applied = pyqtSignal(list, list)  # 一致性应用信号
    
    def __init__(self, character_scene_manager, parent=None):
        super().__init__(parent)
        self.character_scene_manager = character_scene_manager
        self.parent_window = parent
        self.current_character_id = None
        self.current_scene_id = None
        
        # 初始化颜色优化器
        self.color_optimizer = ColorOptimizer()
        
        self.init_ui()
        self.load_data()
        # 使用QTimer延迟加载世界观圣经内容，确保UI完全初始化
        QTimer.singleShot(100, self.load_world_bible_content)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("角色场景设置")
        self.setModal(True)
        # 减小窗口大小并设置最大尺寸
        self.resize(900, 600)
        self.setMaximumSize(1200, 800)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 角色管理标签页
        self.character_tab = self.create_character_tab()
        self.tab_widget.addTab(self.character_tab, "角色管理")
        
        # 场景管理标签页
        self.scene_tab = self.create_scene_tab()
        self.tab_widget.addTab(self.scene_tab, "场景管理")
        
        # 一致性设置标签页
        self.consistency_tab = self.create_consistency_tab()
        self.tab_widget.addTab(self.consistency_tab, "一致性设置")
        
        # 自动提取标签页
        self.extract_tab = self.create_extract_tab()
        self.tab_widget.addTab(self.extract_tab, "自动提取")
        
        main_layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用到分镜")
        self.apply_btn.clicked.connect(self.apply_consistency)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_all_data)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_character_tab(self):
        """创建角色管理标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧：角色列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 角色列表标题和按钮
        char_header_layout = QHBoxLayout()
        char_header_layout.addWidget(QLabel("角色列表"))
        
        self.add_character_btn = QPushButton("添加角色")
        self.add_character_btn.clicked.connect(self.add_character)
        char_header_layout.addWidget(self.add_character_btn)
        
        self.delete_character_btn = QPushButton("删除角色")
        self.delete_character_btn.clicked.connect(self.delete_character)
        char_header_layout.addWidget(self.delete_character_btn)
        
        left_layout.addLayout(char_header_layout)
        
        # 角色列表表格
        self.character_table = QTableWidget()
        self.character_table.setColumnCount(3)
        self.character_table.setHorizontalHeaderLabels(["角色名称", "描述", "来源"])
        
        # 设置列宽
        header = self.character_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.character_table.setColumnWidth(0, 80)  # 角色名称列
        self.character_table.setColumnWidth(1, 120) # 描述列
        self.character_table.setColumnWidth(2, 80)  # 来源列
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 描述列可拉伸
        
        self.character_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.character_table.itemSelectionChanged.connect(self.on_character_selected)
        
        left_layout.addWidget(self.character_table)
        left_widget.setMaximumWidth(320)  # 减小左侧宽度
        
        # 右侧：角色详细信息编辑（添加滚动区域）
        right_scroll = QScrollArea()
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_scroll.setWidget(right_widget)
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 角色基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.char_name_edit = QLineEdit()
        self.char_aliases_edit = QLineEdit()
        self.char_aliases_edit.setPlaceholderText("输入角色的别名或昵称，多个别名用逗号分隔（如：青山,小山）")
        self.char_description_edit = QTextEdit()
        self.char_description_edit.setMaximumHeight(60)  # 减小高度

        basic_layout.addRow("角色名称:", self.char_name_edit)
        basic_layout.addRow("别名/昵称:", self.char_aliases_edit)
        basic_layout.addRow("角色描述:", self.char_description_edit)
        
        right_layout.addWidget(basic_group)
        
        # 外貌信息
        appearance_group = QGroupBox("外貌特征")
        appearance_layout = QFormLayout(appearance_group)
        
        self.char_gender_combo = QComboBox()
        self.char_gender_combo.addItems(["", "男性", "女性", "其他"])
        
        self.char_age_edit = QLineEdit()
        self.char_hair_edit = QLineEdit()
        self.char_eyes_edit = QLineEdit()
        self.char_skin_edit = QLineEdit()
        self.char_build_edit = QLineEdit()
        
        appearance_layout.addRow("性别:", self.char_gender_combo)
        appearance_layout.addRow("年龄范围:", self.char_age_edit)
        appearance_layout.addRow("发型发色:", self.char_hair_edit)
        appearance_layout.addRow("眼睛:", self.char_eyes_edit)
        appearance_layout.addRow("肤色:", self.char_skin_edit)
        appearance_layout.addRow("体型:", self.char_build_edit)
        
        right_layout.addWidget(appearance_group)
        
        # 服装信息
        clothing_group = QGroupBox("服装打扮")
        clothing_layout = QFormLayout(clothing_group)
        
        self.char_clothing_style_edit = QLineEdit()
        self.char_clothing_colors_edit = QLineEdit()
        self.char_accessories_edit = QLineEdit()
        
        # 为颜色输入框添加提示文本和自动优化功能
        self.char_clothing_colors_edit.setPlaceholderText("输入颜色，多个颜色用逗号分隔（系统会自动选择主要颜色）")
        # 当输入框失去焦点时自动优化颜色
        self.char_clothing_colors_edit.editingFinished.connect(self.auto_optimize_colors)
        
        clothing_layout.addRow("服装风格:", self.char_clothing_style_edit)
        
        # 颜色输入框和优化按钮的水平布局
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.char_clothing_colors_edit)
        
        self.optimize_color_btn = QPushButton("优化颜色")
        self.optimize_color_btn.setMaximumWidth(80)
        self.optimize_color_btn.clicked.connect(self.optimize_character_colors)
        self.optimize_color_btn.setToolTip("从多个颜色中自动选择主要颜色")
        color_layout.addWidget(self.optimize_color_btn)
        
        color_widget = QWidget()
        color_widget.setLayout(color_layout)
        clothing_layout.addRow("主要颜色:", color_widget)
        
        clothing_layout.addRow("配饰:", self.char_accessories_edit)
        
        right_layout.addWidget(clothing_group)
        
        # 一致性提示词
        consistency_group = QGroupBox("一致性提示词")
        consistency_layout = QVBoxLayout(consistency_group)
        
        self.char_consistency_edit = QTextEdit()
        self.char_consistency_edit.setMaximumHeight(80)  # 减小高度
        self.char_consistency_edit.setPlaceholderText("输入用于保持角色一致性的提示词...")
        
        consistency_layout.addWidget(self.char_consistency_edit)
        
        # 生成提示词按钮
        generate_char_prompt_btn = QPushButton("自动生成提示词")
        generate_char_prompt_btn.clicked.connect(self.generate_character_prompt)
        consistency_layout.addWidget(generate_char_prompt_btn)
        
        right_layout.addWidget(consistency_group)
        
        # 保存角色按钮
        save_char_btn = QPushButton("保存角色")
        save_char_btn.clicked.connect(self.save_current_character)
        right_layout.addWidget(save_char_btn)
        
        right_layout.addStretch()
        
        # 添加到分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 0)  # 左侧固定宽度
        splitter.setStretchFactor(1, 1)  # 右侧占用剩余空间
        splitter.setSizes([320, 580])    # 设置初始大小比例
        
        layout.addWidget(splitter)
        
        return tab
    
    def create_scene_tab(self):
        """创建场景管理标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧：场景列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 场景列表标题和按钮
        scene_header_layout = QHBoxLayout()
        scene_header_layout.addWidget(QLabel("场景列表"))
        
        self.add_scene_btn = QPushButton("添加场景")
        self.add_scene_btn.clicked.connect(self.add_scene)
        scene_header_layout.addWidget(self.add_scene_btn)
        
        self.delete_scene_btn = QPushButton("删除场景")
        self.delete_scene_btn.clicked.connect(self.delete_scene)
        scene_header_layout.addWidget(self.delete_scene_btn)

        self.clean_scenes_btn = QPushButton("清理临时场景")
        self.clean_scenes_btn.clicked.connect(self.clean_auto_generated_scenes)
        self.clean_scenes_btn.setToolTip("清理分镜生成过程中产生的临时场景数据")
        scene_header_layout.addWidget(self.clean_scenes_btn)
        
        left_layout.addLayout(scene_header_layout)
        
        # 场景列表表格
        self.scene_table = QTableWidget()
        self.scene_table.setColumnCount(3)
        self.scene_table.setHorizontalHeaderLabels(["场景名称", "类型", "来源"])
        
        # 设置列宽
        header = self.scene_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.scene_table.setColumnWidth(0, 100) # 场景名称列
        self.scene_table.setColumnWidth(1, 60)  # 类型列
        self.scene_table.setColumnWidth(2, 80)  # 来源列
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 场景名称列可拉伸
        
        self.scene_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.scene_table.itemSelectionChanged.connect(self.on_scene_selected)
        
        left_layout.addWidget(self.scene_table)
        left_widget.setMaximumWidth(320)  # 减小左侧宽度
        
        # 右侧：场景详细信息编辑（添加滚动区域）
        right_scroll = QScrollArea()
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_scroll.setWidget(right_widget)
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 场景基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.scene_name_edit = QLineEdit()
        self.scene_category_combo = QComboBox()
        self.scene_category_combo.addItems(["", "室内", "室外", "特殊"])
        self.scene_description_edit = QTextEdit()
        self.scene_description_edit.setMaximumHeight(60)  # 减小高度
        
        basic_layout.addRow("场景名称:", self.scene_name_edit)
        basic_layout.addRow("场景类型:", self.scene_category_combo)
        basic_layout.addRow("场景描述:", self.scene_description_edit)
        
        right_layout.addWidget(basic_group)
        
        # 环境信息
        environment_group = QGroupBox("环境设置")
        environment_layout = QFormLayout(environment_group)
        
        self.scene_location_edit = QLineEdit()
        self.scene_size_edit = QLineEdit()
        self.scene_layout_edit = QLineEdit()
        self.scene_decorations_edit = QLineEdit()
        
        environment_layout.addRow("位置类型:", self.scene_location_edit)
        environment_layout.addRow("空间大小:", self.scene_size_edit)
        environment_layout.addRow("布局结构:", self.scene_layout_edit)
        environment_layout.addRow("装饰元素:", self.scene_decorations_edit)
        
        right_layout.addWidget(environment_group)
        
        # 光线氛围
        lighting_group = QGroupBox("光线氛围")
        lighting_layout = QFormLayout(lighting_group)
        
        self.scene_time_combo = QComboBox()
        self.scene_time_combo.addItems(["", "早晨", "上午", "中午", "下午", "傍晚", "晚上", "深夜"])
        
        self.scene_light_source_edit = QLineEdit()
        self.scene_brightness_edit = QLineEdit()
        self.scene_mood_edit = QLineEdit()
        
        lighting_layout.addRow("时间:", self.scene_time_combo)
        lighting_layout.addRow("光源:", self.scene_light_source_edit)
        lighting_layout.addRow("亮度:", self.scene_brightness_edit)
        lighting_layout.addRow("氛围:", self.scene_mood_edit)
        
        right_layout.addWidget(lighting_group)
        
        # 一致性提示词
        consistency_group = QGroupBox("一致性提示词")
        consistency_layout = QVBoxLayout(consistency_group)
        
        self.scene_consistency_edit = QTextEdit()
        self.scene_consistency_edit.setMaximumHeight(80)  # 减小高度
        self.scene_consistency_edit.setPlaceholderText("输入用于保持场景一致性的提示词...")
        
        consistency_layout.addWidget(self.scene_consistency_edit)
        
        # 生成提示词按钮
        generate_scene_prompt_btn = QPushButton("自动生成提示词")
        generate_scene_prompt_btn.clicked.connect(self.generate_scene_prompt)
        consistency_layout.addWidget(generate_scene_prompt_btn)
        
        right_layout.addWidget(consistency_group)
        
        # 保存场景按钮
        save_scene_btn = QPushButton("保存场景")
        save_scene_btn.clicked.connect(self.save_current_scene)
        right_layout.addWidget(save_scene_btn)
        
        right_layout.addStretch()
        
        # 添加到分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 0)  # 左侧固定宽度
        splitter.setStretchFactor(1, 1)  # 右侧占用剩余空间
        splitter.setSizes([320, 580])    # 设置初始大小比例
        
        layout.addWidget(splitter)
        
        return tab
    
    def create_consistency_tab(self):
        """创建一致性设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明标签
        info_label = QLabel("选择要应用到分镜的角色和场景，系统将自动生成一致性提示词")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：角色选择
        char_widget = QWidget()
        char_layout = QVBoxLayout(char_widget)
        char_layout.addWidget(QLabel("选择角色:"))
        
        self.char_selection_table = QTableWidget()
        self.char_selection_table.setColumnCount(3)
        self.char_selection_table.setHorizontalHeaderLabels(["选择", "角色名称", "描述"])
        self.char_selection_table.horizontalHeader().setStretchLastSection(True)
        
        char_layout.addWidget(self.char_selection_table)
        
        # 右侧：场景选择
        scene_widget = QWidget()
        scene_layout = QVBoxLayout(scene_widget)
        scene_layout.addWidget(QLabel("选择场景:"))
        
        self.scene_selection_table = QTableWidget()
        self.scene_selection_table.setColumnCount(3)
        self.scene_selection_table.setHorizontalHeaderLabels(["选择", "场景名称", "类型"])
        self.scene_selection_table.horizontalHeader().setStretchLastSection(True)
        
        scene_layout.addWidget(self.scene_selection_table)
        
        splitter.addWidget(char_widget)
        splitter.addWidget(scene_widget)
        layout.addWidget(splitter)
        
        # 预览区域
        preview_group = QGroupBox("一致性提示词预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.consistency_preview = QTextEdit()
        self.consistency_preview.setMaximumHeight(150)
        self.consistency_preview.setReadOnly(True)
        
        preview_layout.addWidget(self.consistency_preview)
        
        # 生成预览按钮
        generate_preview_btn = QPushButton("生成预览")
        generate_preview_btn.clicked.connect(self.generate_consistency_preview)
        preview_layout.addWidget(generate_preview_btn)
        
        layout.addWidget(preview_group)
        
        return tab
    
    def create_extract_tab(self):
        """创建自动提取标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明
        info_label = QLabel("从世界观圣经中自动提取角色和场景信息")
        info_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        layout.addWidget(info_label)
        
        # 提示信息
        tip_label = QLabel("💡 系统已自动加载世界观圣经内容，您可以直接点击'开始提取'进行分析")
        tip_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin: 5px;")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)
        
        # 文本输入区域
        text_group = QGroupBox("输入文本")
        text_layout = QVBoxLayout(text_group)
        
        self.extract_text_edit = QTextEdit()
        self.extract_text_edit.setPlaceholderText("世界观圣经内容将自动加载到这里，您也可以手动编辑或输入其他文本...")
        text_layout.addWidget(self.extract_text_edit)
        
        # 提取按钮
        extract_btn = QPushButton("开始提取")
        extract_btn.clicked.connect(self.extract_from_text)
        text_layout.addWidget(extract_btn)
        
        layout.addWidget(text_group)
        
        # 提取结果
        result_group = QGroupBox("提取结果")
        result_layout = QVBoxLayout(result_group)
        
        self.extract_result_text = QTextEdit()
        self.extract_result_text.setReadOnly(True)
        result_layout.addWidget(self.extract_result_text)
        
        layout.addWidget(result_group)
        
        return tab
    
    def load_data(self):
        """加载角色和场景数据"""
        self.load_characters()
        self.load_scenes()
        self.load_consistency_selection()
    
    def load_characters(self):
        """加载角色数据到表格"""
        characters = self.character_scene_manager.get_all_characters()
        
        self.character_table.setRowCount(len(characters))
        
        for row, (char_id, char_data) in enumerate(characters.items()):
            # 角色名称
            name_item = QTableWidgetItem(char_data.get('name', ''))
            name_item.setData(Qt.UserRole, char_id)
            self.character_table.setItem(row, 0, name_item)
            
            # 描述
            desc_item = QTableWidgetItem(char_data.get('description', '')[:50] + '...' if len(char_data.get('description', '')) > 50 else char_data.get('description', ''))
            self.character_table.setItem(row, 1, desc_item)
            
            # 来源
            source = "AI提取" if char_data.get('extracted_from_text') else "手动添加"
            if char_data.get('manual_edited'):
                source += "(已编辑)"
            source_item = QTableWidgetItem(source)
            self.character_table.setItem(row, 2, source_item)
    
    def load_scenes(self):
        """加载场景数据到表格"""
        scenes = self.character_scene_manager.get_all_scenes()
        
        self.scene_table.setRowCount(len(scenes))
        
        # 对场景进行自然排序，确保场景1、场景2、场景3、场景4等按正确顺序显示
        import re
        def natural_sort_key(item):
            scene_id, scene_data = item
            scene_name = scene_data.get('name', '')
            # 提取场景名称中的数字进行排序
            numbers = re.findall(r'\d+', scene_name)
            if numbers:
                return (0, int(numbers[0]), scene_name)  # 优先按数字排序
            else:
                return (1, 0, scene_name)  # 非数字场景排在后面
        
        sorted_scenes = sorted(scenes.items(), key=natural_sort_key)
        
        for row, (scene_id, scene_data) in enumerate(sorted_scenes):
            # 场景名称
            name_item = QTableWidgetItem(scene_data.get('name', ''))
            name_item.setData(Qt.UserRole, scene_id)
            self.scene_table.setItem(row, 0, name_item)
            
            # 类型
            category_item = QTableWidgetItem(scene_data.get('category', ''))
            self.scene_table.setItem(row, 1, category_item)
            
            # 来源
            source = "AI提取" if scene_data.get('extracted_from_text') else "手动添加"
            if scene_data.get('manual_edited'):
                source += "(已编辑)"
            source_item = QTableWidgetItem(source)
            self.scene_table.setItem(row, 2, source_item)
    
    def refresh_character_list(self):
        """刷新角色列表显示"""
        self.load_characters()
        self.load_consistency_selection()

    def refresh_scene_list(self):
        """刷新场景列表显示"""
        self.load_scenes()
        self.load_consistency_selection()

    def load_consistency_selection(self):
        """加载一致性选择表格"""
        # 加载角色选择表格
        characters = self.character_scene_manager.get_all_characters()
        self.char_selection_table.setRowCount(len(characters))

        for row, (char_id, char_data) in enumerate(characters.items()):
            # 复选框
            checkbox = QCheckBox()
            self.char_selection_table.setCellWidget(row, 0, checkbox)

            # 角色名称
            name_item = QTableWidgetItem(char_data.get('name', ''))
            name_item.setData(Qt.UserRole, char_id)
            self.char_selection_table.setItem(row, 1, name_item)

            # 描述
            desc_item = QTableWidgetItem(char_data.get('description', '')[:30] + '...' if len(char_data.get('description', '')) > 30 else char_data.get('description', ''))
            self.char_selection_table.setItem(row, 2, desc_item)
        
        # 加载场景选择表格
        scenes = self.character_scene_manager.get_all_scenes()
        self.scene_selection_table.setRowCount(len(scenes))
        
        # 对场景进行自然排序，确保场景1、场景2、场景3、场景4等按正确顺序显示
        def natural_sort_key_selection(item):
            scene_id, scene_data = item
            scene_name = scene_data.get('name', '')
            # 提取场景名称中的数字进行排序
            numbers = re.findall(r'\d+', scene_name)
            if numbers:
                return (0, int(numbers[0]), scene_name)  # 优先按数字排序
            else:
                return (1, 0, scene_name)  # 非数字场景排在后面
        
        sorted_scenes_selection = sorted(scenes.items(), key=natural_sort_key_selection)
        
        for row, (scene_id, scene_data) in enumerate(sorted_scenes_selection):
            # 复选框
            checkbox = QCheckBox()
            self.scene_selection_table.setCellWidget(row, 0, checkbox)
            
            # 场景名称
            name_item = QTableWidgetItem(scene_data.get('name', ''))
            name_item.setData(Qt.UserRole, scene_id)
            self.scene_selection_table.setItem(row, 1, name_item)
            
            # 类型
            category_item = QTableWidgetItem(scene_data.get('category', ''))
            self.scene_selection_table.setItem(row, 2, category_item)
    
    def on_character_selected(self):
        """角色选择改变时的处理"""
        current_row = self.character_table.currentRow()
        if current_row >= 0:
            name_item = self.character_table.item(current_row, 0)
            if name_item:
                char_id = name_item.data(Qt.UserRole)
                self.load_character_details(char_id)
    
    def on_scene_selected(self):
        """场景选择改变时的处理"""
        current_row = self.scene_table.currentRow()
        if current_row >= 0:
            name_item = self.scene_table.item(current_row, 0)
            if name_item:
                scene_id = name_item.data(Qt.UserRole)
                self.load_scene_details(scene_id)
    
    def load_character_details(self, char_id):
        """加载角色详细信息"""
        try:
            self.current_character_id = char_id
            char_data = self.character_scene_manager.get_character(char_id)

            if not char_data:
                logger.warning(f"未找到角色数据: {char_id}")
                return

            # 检查char_data是否为字典
            if not isinstance(char_data, dict):
                logger.error(f"角色数据格式错误，期望字典但得到: {type(char_data)}, 内容: {char_data}")
                QMessageBox.warning(self, "数据错误", f"角色数据格式错误: {type(char_data)}")
                return

            # 安全地获取基本信息
            self.char_name_edit.setText(str(char_data.get('name', '')))

            # 加载别名
            aliases = char_data.get('aliases', [])
            if isinstance(aliases, list):
                self.char_aliases_edit.setText(', '.join(str(a) for a in aliases))
            else:
                self.char_aliases_edit.setText(str(aliases) if aliases else '')

            self.char_description_edit.setText(str(char_data.get('description', '')))

            # 外貌信息 - 处理可能是字符串或字典的情况
            appearance = char_data.get('appearance', {})
            if isinstance(appearance, str):
                # 如果是字符串，创建一个基本的字典结构
                appearance = {'description': appearance}
            elif not isinstance(appearance, dict):
                # 如果既不是字符串也不是字典，使用空字典
                logger.warning(f"外貌数据格式异常: {type(appearance)}, 内容: {appearance}")
                appearance = {}

            # 安全地设置外貌信息
            self.char_gender_combo.setCurrentText(str(appearance.get('gender', '')))
            self.char_age_edit.setText(str(appearance.get('age_range', '')))
            self.char_hair_edit.setText(str(appearance.get('hair', '')))
            self.char_eyes_edit.setText(str(appearance.get('eyes', '')))
            self.char_skin_edit.setText(str(appearance.get('skin', '')))
            self.char_build_edit.setText(str(appearance.get('build', '')))
            
            # 服装信息 - 处理可能是字符串或字典的情况
            clothing = char_data.get('clothing', {})
            if isinstance(clothing, str):
                # 如果是字符串，创建一个基本的字典结构
                clothing = {'description': clothing}
            elif not isinstance(clothing, dict):
                # 如果既不是字符串也不是字典，使用空字典
                clothing = {}

            self.char_clothing_style_edit.setText(clothing.get('style', ''))
            
            # 颜色信息处理 - 智能优化为单一主要颜色
            colors = clothing.get('colors', [])
            if colors:
                if len(colors) > 1:
                    # 如果有多个颜色，自动选择主要颜色
                    color_text = ', '.join(colors)
                    primary_color = self.color_optimizer.extract_primary_color(color_text)
                    if primary_color and primary_color != color_text:
                        self.char_clothing_colors_edit.setText(primary_color)
                        # 自动更新角色数据中的颜色
                        char_data['clothing']['colors'] = [primary_color]

                        # 同步更新一致性提示词中的颜色描述
                        consistency_prompt = char_data.get('consistency_prompt', '')
                        if consistency_prompt:
                            # 使用颜色优化器更新一致性提示词中的颜色描述
                            updated_prompt = self.color_optimizer.apply_color_consistency_to_description(
                                consistency_prompt, char_data.get('name', ''), primary_color
                            )
                            # 只有在真正有变化时才更新和保存
                            if updated_prompt != consistency_prompt:
                                char_data['consistency_prompt'] = updated_prompt
                                logger.info(f"同步更新一致性提示词: {consistency_prompt} -> {updated_prompt}")
                                self.character_scene_manager.save_character(char_id, char_data)
                                logger.info(f"自动优化角色 {char_data.get('name', '')} 的颜色: {color_text} -> {primary_color}")
                            else:
                                logger.debug(f"角色 {char_data.get('name', '')} 的一致性提示词已符合颜色要求，无需更新")
                        else:
                            # 没有一致性提示词时，只更新颜色数据
                            self.character_scene_manager.save_character(char_id, char_data)
                            logger.info(f"自动优化角色 {char_data.get('name', '')} 的颜色: {color_text} -> {primary_color}")
                    else:
                        self.char_clothing_colors_edit.setText(', '.join(colors))
                else:
                    self.char_clothing_colors_edit.setText(colors[0])
            else:
                self.char_clothing_colors_edit.setText('')
            
            self.char_accessories_edit.setText(', '.join(clothing.get('accessories', [])))
            
            # 一致性提示词
            self.char_consistency_edit.setText(str(char_data.get('consistency_prompt', '')))

        except Exception as e:
            logger.error(f"加载角色详细信息失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"加载角色信息失败: {str(e)}")
            # 清空所有字段
            self.clear_character_details()

    def clear_character_details(self):
        """清空角色详细信息"""
        try:
            self.current_character_id = None
            self.char_name_edit.setText('')
            self.char_aliases_edit.setText('')
            self.char_description_edit.setText('')
            self.char_gender_combo.setCurrentText('')
            self.char_age_edit.setText('')
            self.char_hair_edit.setText('')
            self.char_eyes_edit.setText('')
            self.char_skin_edit.setText('')
            self.char_build_edit.setText('')
            self.char_clothing_style_edit.setText('')
            self.char_clothing_colors_edit.setText('')
            self.char_accessories_edit.setText('')
            self.char_consistency_edit.setText('')
        except Exception as e:
            logger.error(f"清空角色详细信息失败: {e}")
    
    def load_scene_details(self, scene_id):
        """加载场景详细信息"""
        self.current_scene_id = scene_id
        scene_data = self.character_scene_manager.get_scene(scene_id)
        
        if scene_data:
            self.scene_name_edit.setText(scene_data.get('name', ''))
            self.scene_category_combo.setCurrentText(scene_data.get('category', ''))
            self.scene_description_edit.setText(scene_data.get('description', ''))
            
            # 环境信息 - 处理可能是字符串或字典的情况
            environment = scene_data.get('environment', {})
            if isinstance(environment, str):
                # 如果是字符串，创建一个基本的字典结构
                environment = {'description': environment}
            elif not isinstance(environment, dict):
                # 如果既不是字符串也不是字典，使用空字典
                environment = {}

            self.scene_location_edit.setText(environment.get('location_type', ''))
            self.scene_size_edit.setText(environment.get('size', ''))
            self.scene_layout_edit.setText(environment.get('layout', ''))
            decorations = environment.get('decorations', [])
            if isinstance(decorations, list):
                self.scene_decorations_edit.setText(', '.join(decorations))
            else:
                self.scene_decorations_edit.setText(str(decorations))

            # 光线信息 - 处理可能是字符串或字典的情况
            lighting = scene_data.get('lighting', {})
            if isinstance(lighting, str):
                # 如果是字符串，创建一个基本的字典结构
                lighting = {'description': lighting}
            elif not isinstance(lighting, dict):
                # 如果既不是字符串也不是字典，使用空字典
                lighting = {}

            self.scene_time_combo.setCurrentText(lighting.get('time_of_day', ''))
            self.scene_light_source_edit.setText(lighting.get('light_source', ''))
            self.scene_brightness_edit.setText(lighting.get('brightness', ''))
            self.scene_mood_edit.setText(lighting.get('mood', ''))
            
            # 一致性提示词
            self.scene_consistency_edit.setText(scene_data.get('consistency_prompt', ''))
    
    def add_character(self):
        """添加新角色"""
        char_id = f"manual_{self.character_scene_manager._get_current_time().replace(':', '_')}"
        char_data = {
            "name": "新角色",
            "aliases": [],
            "description": "",
            "appearance": {
                "gender": "",
                "age_range": "",
                "hair": "",
                "eyes": "",
                "skin": "",
                "build": ""
            },
            "clothing": {
                "style": "",
                "colors": [],
                "accessories": []
            },
            "personality": {
                "traits": [],
                "expressions": [],
                "mannerisms": []
            },
            "consistency_prompt": "",
            "extracted_from_text": False,
            "manual_edited": False
        }
        
        self.character_scene_manager.save_character(char_id, char_data)
        self.load_characters()
        self.load_consistency_selection()

        # 触发同步通知
        notify_character_changed(char_id, char_data, 'add')

        # 选中新添加的角色
        for row in range(self.character_table.rowCount()):
            item = self.character_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == char_id:
                self.character_table.selectRow(row)
                break
    
    def add_scene(self):
        """添加新场景"""
        # 🔧 修复：使用"镜头场景_"而不是"分镜场景_"
        scene_id = f"镜头场景_手动添加_{self.character_scene_manager._get_current_time().replace(':', '_')}"
        scene_data = {
            "name": "新场景",
            "category": "",
            "description": "",
            "environment": {
                "location_type": "",
                "size": "",
                "layout": "",
                "decorations": [],
                "furniture": []
            },
            "lighting": {
                "time_of_day": "",
                "light_source": "",
                "brightness": "",
                "mood": ""
            },
            "atmosphere": {
                "style": "",
                "colors": [],
                "mood": "",
                "weather": ""
            },
            "consistency_prompt": "",
            "extracted_from_text": False,
            "manual_edited": False
        }
        
        self.character_scene_manager.save_scene(scene_id, scene_data)
        self.load_scenes()
        self.load_consistency_selection()

        # 触发同步通知
        notify_scene_changed(scene_id, scene_data, 'add')

        # 选中新添加的场景
        for row in range(self.scene_table.rowCount()):
            item = self.scene_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == scene_id:
                self.scene_table.selectRow(row)
                break
    
    def delete_character(self):
        """删除选中的角色"""
        current_row = self.character_table.currentRow()
        if current_row >= 0:
            name_item = self.character_table.item(current_row, 0)
            if name_item:
                char_id = name_item.data(Qt.UserRole)
                char_name = name_item.text()
                
                reply = QMessageBox.question(self, "确认删除", 
                                            f"确定要删除角色 '{char_name}' 吗？",
                                            QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.character_scene_manager.delete_character(char_id)
                    self.load_characters()
                    self.load_consistency_selection()
                    self.clear_character_details()

                    # 触发同步通知
                    notify_character_changed(char_id, {'name': char_name}, 'delete')
    
    def delete_scene(self):
        """删除选中的场景"""
        current_row = self.scene_table.currentRow()
        if current_row >= 0:
            name_item = self.scene_table.item(current_row, 0)
            if name_item:
                scene_id = name_item.data(Qt.UserRole)
                scene_name = name_item.text()
                
                reply = QMessageBox.question(self, "确认删除", 
                                            f"确定要删除场景 '{scene_name}' 吗？",
                                            QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.character_scene_manager.delete_scene(scene_id)
                    self.load_scenes()
                    self.load_consistency_selection()
                    self.clear_scene_details()

                    # 触发同步通知
                    notify_scene_changed(scene_id, {'name': scene_name}, 'delete')

    def clean_auto_generated_scenes(self):
        """清理自动生成的临时场景数据"""
        try:
            reply = QMessageBox.question(
                self, "确认清理",
                "确定要清理所有自动生成的临时场景数据吗？\n"
                "这将删除分镜生成过程中产生的临时场景，不会影响您手动创建的场景。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                cleaned_count = self.character_scene_manager.clean_auto_generated_scenes()
                self.load_scenes()
                self.load_consistency_selection()
                self.clear_scene_details()
                QMessageBox.information(
                    self, "清理完成",
                    f"成功清理了 {cleaned_count} 个临时场景数据"
                )
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清理失败: {e}")

    def auto_optimize_colors(self):
        """自动优化颜色 - 当输入框失去焦点时自动执行"""
        try:
            color_text = self.char_clothing_colors_edit.text().strip()
            if not color_text:
                return
            
            # 检查是否包含多个颜色（包含逗号或多个颜色词）
            if ',' in color_text or len([c for c in color_text.split() if any(color in c for color in self.color_optimizer.color_priority.keys())]) > 1:
                # 提取主要颜色
                primary_color = self.color_optimizer.extract_primary_color(color_text)
                
                if primary_color and primary_color != color_text:
                    self.char_clothing_colors_edit.setText(primary_color)
                    
                    # 同步更新一致性提示词
                    consistency_text = self.char_consistency_edit.toPlainText()
                    if consistency_text and self.current_character_id:
                        char_data = self.character_scene_manager.get_character(self.current_character_id)
                        if char_data:
                            updated_prompt = self.color_optimizer.apply_color_consistency_to_description(
                                consistency_text, char_data.get('name', ''), primary_color
                            )
                            self.char_consistency_edit.setText(updated_prompt)
                            logger.info(f"自动优化时同步更新一致性提示词")
                    
                    # 静默优化，不显示消息框
                    logger.info(f"自动优化颜色: {color_text} -> {primary_color}")
                    
        except Exception as e:
            logger.error(f"自动颜色优化失败: {e}")
    
    def optimize_character_colors(self):
        """手动优化角色颜色"""
        try:
            color_text = self.char_clothing_colors_edit.text().strip()
            if not color_text:
                QMessageBox.information(self, "提示", "请先输入颜色信息")
                return
            
            # 提取主要颜色
            primary_color = self.color_optimizer.extract_primary_color(color_text)
            
            if primary_color:
                self.char_clothing_colors_edit.setText(primary_color)
                QMessageBox.information(self, "颜色优化完成", f"已将主要颜色设置为: {primary_color}")
            else:
                QMessageBox.warning(self, "优化失败", "无法识别有效的颜色信息")
                
        except Exception as e:
            logger.error(f"颜色优化失败: {e}")
            QMessageBox.critical(self, "错误", f"颜色优化失败: {str(e)}")
    
    def save_current_character(self):
        """保存当前编辑的角色"""
        if not self.current_character_id:
            QMessageBox.warning(self, "警告", "请先选择一个角色")
            return
        
        try:
            # 构建角色数据
            char_data = {
                "name": self.char_name_edit.text(),
                "aliases": [a.strip() for a in self.char_aliases_edit.text().split(',') if a.strip()],
                "description": self.char_description_edit.toPlainText(),
                "appearance": {
                    "gender": self.char_gender_combo.currentText(),
                    "age_range": self.char_age_edit.text(),
                    "hair": self.char_hair_edit.text(),
                    "eyes": self.char_eyes_edit.text(),
                    "skin": self.char_skin_edit.text(),
                    "build": self.char_build_edit.text()
                },
                "clothing": {
                    "style": self.char_clothing_style_edit.text(),
                    "colors": [c.strip() for c in self.char_clothing_colors_edit.text().split(',') if c.strip()],
                    "accessories": [a.strip() for a in self.char_accessories_edit.text().split(',') if a.strip()]
                },
                "consistency_prompt": self.char_consistency_edit.toPlainText(),
                "manual_edited": True
            }
            
            # 自动优化颜色（确保只有一个主要颜色）
            original_colors = char_data.get('clothing', {}).get('colors', [])
            char_data = self.color_optimizer.optimize_character_colors(char_data)
            optimized_colors = char_data.get('clothing', {}).get('colors', [])
            
            # 如果颜色发生了变化，同步更新一致性提示词
            if original_colors != optimized_colors and optimized_colors:
                primary_color = optimized_colors[0]
                consistency_prompt = char_data.get('consistency_prompt', '')
                if consistency_prompt:
                    updated_prompt = self.color_optimizer.apply_color_consistency_to_description(
                        consistency_prompt, char_data.get('name', ''), primary_color
                    )
                    # 只有在真正有变化时才更新
                    if updated_prompt != consistency_prompt:
                        char_data['consistency_prompt'] = updated_prompt
                        logger.info(f"保存时同步更新一致性提示词，主要颜色: {primary_color}")
                    else:
                        logger.debug(f"一致性提示词已符合颜色要求，无需更新")
            
            # 保留原有的其他字段
            original_data = self.character_scene_manager.get_character(self.current_character_id)
            if original_data:
                char_data.update({
                    "personality": original_data.get("personality", {}),
                    "extracted_from_text": original_data.get("extracted_from_text", False)
                })
            
            self.character_scene_manager.save_character(self.current_character_id, char_data)
            self.load_characters()
            self.load_consistency_selection()

            # 触发同步通知
            notify_character_changed(self.current_character_id, char_data, 'update')

            # 显示优化后的颜色信息
            optimized_colors = char_data.get('clothing', {}).get('colors', [])
            if optimized_colors:
                color_info = f"角色信息已保存\n主要服装颜色: {optimized_colors[0]}"
            else:
                color_info = "角色信息已保存"

            QMessageBox.information(self, "成功", color_info)
            
        except Exception as e:
            logger.error(f"保存角色失败: {e}")
            QMessageBox.critical(self, "错误", f"保存角色失败: {str(e)}")
    
    def save_current_scene(self):
        """保存当前编辑的场景"""
        if not self.current_scene_id:
            QMessageBox.warning(self, "警告", "请先选择一个场景")
            return
        
        try:
            scene_data = {
                "name": self.scene_name_edit.text(),
                "category": self.scene_category_combo.currentText(),
                "description": self.scene_description_edit.toPlainText(),
                "environment": {
                    "location_type": self.scene_location_edit.text(),
                    "size": self.scene_size_edit.text(),
                    "layout": self.scene_layout_edit.text(),
                    "decorations": [d.strip() for d in self.scene_decorations_edit.text().split(',') if d.strip()]
                },
                "lighting": {
                    "time_of_day": self.scene_time_combo.currentText(),
                    "light_source": self.scene_light_source_edit.text(),
                    "brightness": self.scene_brightness_edit.text(),
                    "mood": self.scene_mood_edit.text()
                },
                "consistency_prompt": self.scene_consistency_edit.toPlainText(),
                "manual_edited": True
            }
            
            # 保留原有的其他字段
            original_data = self.character_scene_manager.get_scene(self.current_scene_id)
            if original_data:
                scene_data.update({
                    "atmosphere": original_data.get("atmosphere", {}),
                    "extracted_from_text": original_data.get("extracted_from_text", False)
                })
            
            self.character_scene_manager.save_scene(self.current_scene_id, scene_data)
            self.load_scenes()
            self.load_consistency_selection()

            # 触发同步通知
            notify_scene_changed(self.current_scene_id, scene_data, 'update')

            QMessageBox.information(self, "成功", "场景信息已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存场景失败: {str(e)}")
    
    def generate_character_prompt(self):
        """自动生成角色一致性提示词"""
        try:
            prompt_parts = []
            
            # 基本信息
            name = self.char_name_edit.text()
            if name:
                prompt_parts.append(f"角色名称: {name}")
            
            # 外貌特征
            appearance_parts = []
            if self.char_gender_combo.currentText():
                appearance_parts.append(self.char_gender_combo.currentText())
            if self.char_age_edit.text():
                appearance_parts.append(f"{self.char_age_edit.text()}岁")
            if self.char_hair_edit.text():
                appearance_parts.append(self.char_hair_edit.text())
            if self.char_eyes_edit.text():
                appearance_parts.append(self.char_eyes_edit.text())
            if self.char_skin_edit.text():
                appearance_parts.append(self.char_skin_edit.text())
            if self.char_build_edit.text():
                appearance_parts.append(self.char_build_edit.text())
            
            if appearance_parts:
                prompt_parts.append(f"外貌: {', '.join(appearance_parts)}")
            
            # 服装
            clothing_parts = []
            if self.char_clothing_style_edit.text():
                clothing_parts.append(self.char_clothing_style_edit.text())
            if self.char_clothing_colors_edit.text():
                clothing_parts.append(f"颜色: {self.char_clothing_colors_edit.text()}")
            if self.char_accessories_edit.text():
                clothing_parts.append(f"配饰: {self.char_accessories_edit.text()}")
            
            if clothing_parts:
                prompt_parts.append(f"服装: {', '.join(clothing_parts)}")
            
            generated_prompt = '; '.join(prompt_parts)
            self.char_consistency_edit.setText(generated_prompt)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成提示词失败: {str(e)}")
    
    def generate_scene_prompt(self):
        """自动生成场景一致性提示词"""
        try:
            prompt_parts = []
            
            # 基本信息
            name = self.scene_name_edit.text()
            if name:
                prompt_parts.append(f"场景: {name}")
            
            category = self.scene_category_combo.currentText()
            if category:
                prompt_parts.append(f"类型: {category}")
            
            # 环境信息
            environment_parts = []
            if self.scene_location_edit.text():
                environment_parts.append(self.scene_location_edit.text())
            if self.scene_size_edit.text():
                environment_parts.append(f"大小: {self.scene_size_edit.text()}")
            if self.scene_layout_edit.text():
                environment_parts.append(f"布局: {self.scene_layout_edit.text()}")
            if self.scene_decorations_edit.text():
                environment_parts.append(f"装饰: {self.scene_decorations_edit.text()}")
            
            if environment_parts:
                prompt_parts.append(f"环境: {', '.join(environment_parts)}")
            
            # 光线氛围
            lighting_parts = []
            if self.scene_time_combo.currentText():
                lighting_parts.append(self.scene_time_combo.currentText())
            if self.scene_light_source_edit.text():
                lighting_parts.append(f"光源: {self.scene_light_source_edit.text()}")
            if self.scene_brightness_edit.text():
                lighting_parts.append(f"亮度: {self.scene_brightness_edit.text()}")
            if self.scene_mood_edit.text():
                lighting_parts.append(f"氛围: {self.scene_mood_edit.text()}")
            
            if lighting_parts:
                prompt_parts.append(f"光线: {', '.join(lighting_parts)}")
            
            generated_prompt = '; '.join(prompt_parts)
            self.scene_consistency_edit.setText(generated_prompt)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成提示词失败: {str(e)}")
    
    def generate_consistency_preview(self):
        """生成一致性预览"""
        try:
            selected_characters = []
            selected_scenes = []
            
            # 获取选中的角色
            for row in range(self.char_selection_table.rowCount()):
                checkbox = self.char_selection_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    name_item = self.char_selection_table.item(row, 1)
                    if name_item:
                        char_id = name_item.data(Qt.UserRole)
                        selected_characters.append(char_id)
            
            # 获取选中的场景
            for row in range(self.scene_selection_table.rowCount()):
                checkbox = self.scene_selection_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    name_item = self.scene_selection_table.item(row, 1)
                    if name_item:
                        scene_id = name_item.data(Qt.UserRole)
                        selected_scenes.append(scene_id)
            
            # 生成一致性提示词
            consistency_prompt = self.character_scene_manager.generate_consistency_prompt(
                selected_characters, selected_scenes
            )
            
            self.consistency_preview.setText(consistency_prompt)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成预览失败: {str(e)}")
    
    def extract_from_text(self):
        """从文本中提取角色和场景"""
        text = self.extract_text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要分析的文本")
            return

        # 创建进度对话框
        self.progress_dialog = QProgressDialog("正在提取角色和场景信息...", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("提取进度")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()

        # 在后台线程中执行提取
        self.extract_thread = ExtractionThread(self.character_scene_manager, text)
        self.extract_thread.finished.connect(self.on_extraction_finished)
        self.extract_thread.error.connect(self.on_extraction_error)

        # 连接取消按钮
        self.progress_dialog.canceled.connect(self.cancel_extraction)

        self.extract_thread.start()

    def cancel_extraction(self):
        """取消提取操作"""
        if hasattr(self, 'extract_thread') and self.extract_thread.isRunning():
            self.extract_thread.cancel()
            self.extract_thread.quit()
            self.extract_thread.wait()

        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

    def on_extraction_finished(self, result):
        """提取完成处理"""
        try:
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.close()

            if result['success']:
                self.extract_result_text.setText(f"提取成功！\n{result['message']}")
                self.load_data()  # 重新加载所有数据
                QMessageBox.information(self, "成功", result['message'])
            else:
                self.extract_result_text.setText(f"提取失败：{result['message']}")
                QMessageBox.critical(self, "错误", result['message'])

        except Exception as e:
            logger.error(f"处理提取结果时出错: {e}")
            QMessageBox.critical(self, "错误", f"处理提取结果时出错: {str(e)}")

    def on_extraction_error(self, error_msg):
        """提取错误处理"""
        try:
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.close()

            error_text = f"提取过程中发生错误: {error_msg}"
            self.extract_result_text.setText(error_text)
            QMessageBox.critical(self, "错误", error_text)

        except Exception as e:
            logger.error(f"处理提取错误时出错: {e}")

    def load_world_bible_content(self):
        """加载世界观圣经内容到自动提取界面"""
        try:
            world_bible_text = None
            logger.info("开始加载世界观圣经内容...")

            # 方法1：优先直接从项目文件读取 project.json
            if (hasattr(self.parent_window, 'project_manager') and
                    self.parent_window.project_manager and
                    self.parent_window.project_manager.current_project):
                project_data = self.parent_window.project_manager.current_project
                logger.info(f"项目数据包含的键: {list(project_data.keys())}")

                if 'five_stage_storyboard' in project_data:
                    five_stage_data = project_data['five_stage_storyboard']
                    logger.info(f"五阶段数据包含的键: {list(five_stage_data.keys())}")

                    if 'stage_data' in five_stage_data:
                        stage_data = five_stage_data['stage_data']
                        logger.info(f"阶段数据包含的键: {list(stage_data.keys())}")

                        if '1' in stage_data:
                            stage1_data = stage_data['1']
                            logger.info(f"阶段1数据包含的键: {list(stage1_data.keys()) if isinstance(stage1_data, dict) else '非字典类型'}")

                            if 'world_bible' in stage1_data:
                                world_bible_text = stage1_data['world_bible']
                                if world_bible_text:
                                    logger.info(f"从项目文件 project.json 直接读取world_bible内容，长度: {len(world_bible_text)}")
                                else:
                                    logger.info("项目文件中world_bible字段存在但内容为空")
                            else:
                                logger.info("阶段1数据中未找到world_bible字段")
                        else:
                            logger.info("阶段数据中未找到阶段1")
                    else:
                        logger.info("五阶段数据中未找到stage_data字段")
                else:
                    logger.info("项目数据中未找到five_stage_storyboard字段")
            else:
                logger.info("未找到项目管理器或当前项目")

            # 方法2：从父窗口的stage_data获取
            if not world_bible_text and (hasattr(self.parent_window, 'stage_data') and
                '1' in self.parent_window.stage_data and
                'world_bible' in self.parent_window.stage_data['1']):

                world_bible_text = self.parent_window.stage_data['1']['world_bible']
                if world_bible_text:
                    logger.info("从父窗口stage_data获取world_bible内容")

            # 方法3：从父窗口的world_bible_output组件获取
            if not world_bible_text and (hasattr(self.parent_window, 'world_bible_output') and
                  self.parent_window.world_bible_output.toPlainText()):

                world_bible_text = self.parent_window.world_bible_output.toPlainText()
                if world_bible_text:
                    logger.info("从父窗口world_bible_output获取内容")

            # 方法4：从五阶段分镜标签页获取
            if not world_bible_text and hasattr(self.parent_window, 'five_stage_storyboard_tab'):
                five_stage_tab = self.parent_window.five_stage_storyboard_tab
                if hasattr(five_stage_tab, 'stage_data') and '1' in five_stage_tab.stage_data:
                    stage1_data = five_stage_tab.stage_data['1']
                    if 'world_bible' in stage1_data:
                        world_bible_text = stage1_data['world_bible']
                        if world_bible_text:
                            logger.info("从五阶段分镜标签页获取world_bible内容")

            # 方法5：从五阶段分镜标签页的world_bible_output组件获取
            if not world_bible_text and hasattr(self.parent_window, 'five_stage_storyboard_tab'):
                five_stage_tab = self.parent_window.five_stage_storyboard_tab
                if hasattr(five_stage_tab, 'world_bible_output') and five_stage_tab.world_bible_output:
                    world_bible_text = five_stage_tab.world_bible_output.toPlainText()
                    if world_bible_text:
                        logger.info("从五阶段分镜标签页的world_bible_output组件获取内容")

            # 设置到文本编辑框
            if world_bible_text and hasattr(self, 'extract_text_edit'):
                self.extract_text_edit.setText(world_bible_text)
                logger.info(f"已自动加载世界观圣经内容到自动提取界面，内容长度: {len(world_bible_text)}")
            else:
                logger.info("未找到世界观圣经内容或extract_text_edit组件不存在")
                # 如果仍然没有找到内容，显示提示信息
                if hasattr(self, 'extract_text_edit'):
                    self.extract_text_edit.setPlaceholderText(
                        "未能自动加载世界观圣经内容。\n\n"
                        "请确保已在第一阶段完成世界观圣经生成，\n"
                        "或者手动在此处输入要分析的文本内容。"
                    )

        except Exception as e:
            logger.warning(f"加载世界观圣经内容时出错: {e}")
            # 出错时也设置提示信息
            if hasattr(self, 'extract_text_edit'):
                self.extract_text_edit.setPlaceholderText(
                    "加载世界观圣经内容时出现错误。\n\n"
                    "请手动在此处输入要分析的文本内容。"
                )
    
    def apply_consistency(self):
        """应用一致性设置到分镜"""
        try:
            selected_characters = []
            selected_scenes = []
            
            # 获取选中的角色
            for row in range(self.char_selection_table.rowCount()):
                checkbox = self.char_selection_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    name_item = self.char_selection_table.item(row, 1)
                    if name_item:
                        char_id = name_item.data(Qt.UserRole)
                        selected_characters.append(char_id)
            
            # 获取选中的场景
            for row in range(self.scene_selection_table.rowCount()):
                checkbox = self.scene_selection_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    name_item = self.scene_selection_table.item(row, 1)
                    if name_item:
                        scene_id = name_item.data(Qt.UserRole)
                        selected_scenes.append(scene_id)
            
            if not selected_characters and not selected_scenes:
                QMessageBox.warning(self, "警告", "请至少选择一个角色或场景")
                return
            
            # 发射信号
            self.consistency_applied.emit(selected_characters, selected_scenes)
            
            QMessageBox.information(self, "成功", "一致性设置已应用到分镜")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用一致性设置失败: {str(e)}")
    
    def save_all_data(self):
        """保存所有数据"""
        try:
            # 如果当前有编辑的角色，先保存
            if self.current_character_id:
                self.save_current_character()
            
            # 如果当前有编辑的场景，先保存
            if self.current_scene_id:
                self.save_current_scene()
            
            QMessageBox.information(self, "成功", "所有数据已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存数据失败: {str(e)}")
    
    def clear_character_details(self):
        """清空角色详细信息"""
        self.current_character_id = None
        self.char_name_edit.clear()
        self.char_description_edit.clear()
        self.char_gender_combo.setCurrentIndex(0)
        self.char_age_edit.clear()
        self.char_hair_edit.clear()
        self.char_eyes_edit.clear()
        self.char_skin_edit.clear()
        self.char_build_edit.clear()
        self.char_clothing_style_edit.clear()
        self.char_clothing_colors_edit.clear()
        self.char_accessories_edit.clear()
        self.char_consistency_edit.clear()
    
    def clear_scene_details(self):
        """清空场景详细信息"""
        self.current_scene_id = None
        self.scene_name_edit.clear()
        self.scene_category_combo.setCurrentIndex(0)
        self.scene_description_edit.clear()
        self.scene_location_edit.clear()
        self.scene_size_edit.clear()
        self.scene_layout_edit.clear()
        self.scene_decorations_edit.clear()
        self.scene_time_combo.setCurrentIndex(0)
        self.scene_light_source_edit.clear()
        self.scene_brightness_edit.clear()
        self.scene_mood_edit.clear()
        self.scene_consistency_edit.clear()