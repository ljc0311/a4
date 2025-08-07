import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from src.utils.config_manager import ConfigManager
from src.utils.logger import logger

class ModelSettingsUI:
    def __init__(self, parent):
        self.parent = parent
        self.config_manager = ConfigManager()
        
        # 创建模型设置框架
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建模型列表
        self.create_model_list()
        
        # 创建模型编辑区域
        self.create_model_edit_area()
        
        # 加载模型列表
        self.load_models()
    
    def create_model_list(self):
        # 创建模型列表框架
        list_frame = ttk.LabelFrame(self.frame, text="模型列表")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建模型列表
        self.model_listbox = tk.Listbox(list_frame, width=30)
        self.model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.model_listbox.bind('<<ListboxSelect>>', self.on_model_select)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.model_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.model_listbox.config(yscrollcommand=scrollbar.set)
        
        # 创建按钮框架
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # 添加按钮
        ttk.Button(btn_frame, text="添加", command=self.add_model).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_model).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="刷新", command=self.load_models).pack(side=tk.LEFT, padx=2)
    
    def create_model_edit_area(self):
        # 创建模型编辑框架
        edit_frame = ttk.LabelFrame(self.frame, text="模型配置")
        edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建表单
        form_frame = ttk.Frame(edit_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 模型名称
        ttk.Label(form_frame, text="模型名称:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 模型类型
        ttk.Label(form_frame, text="模型类型:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.type_var = tk.StringVar()
        model_types = ["deepseek", "tongyi", "zhipu", "google", "openai", "custom"]
        ttk.Combobox(form_frame, textvariable=self.type_var, values=model_types).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # API密钥
        ttk.Label(form_frame, text="API密钥:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.key_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.key_var, show="*").grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # API URL
        ttk.Label(form_frame, text="API URL:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.url_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.url_var).grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 保存按钮
        ttk.Button(form_frame, text="保存", command=self.save_model).grid(row=4, column=0, columnspan=2, pady=10)
        
        # 配置网格权重
        form_frame.columnconfigure(1, weight=1)
    
    def load_models(self):
        """加载模型列表"""
        self.model_listbox.delete(0, tk.END)
        models = self.config_manager.get_models()
        for model in models:
            self.model_listbox.insert(tk.END, model.get("name", "未命名模型"))
    
    def on_model_select(self, event):
        """选择模型时的处理函数"""
        if not self.model_listbox.curselection():
            return
        
        index = self.model_listbox.curselection()[0]
        model_name = self.model_listbox.get(index)
        model = self.config_manager.get_model_by_name(model_name)
        
        if model:
            self.name_var.set(model.get("name", ""))
            self.type_var.set(model.get("type", ""))
            self.key_var.set(model.get("key", ""))
            self.url_var.set(model.get("url", ""))
    
    def add_model(self):
        """添加新模型"""
        # 清空表单
        self.name_var.set("")
        self.type_var.set("")
        self.key_var.set("")
        self.url_var.set("")
    
    def delete_model(self):
        """删除选中的模型"""
        if not self.model_listbox.curselection():
            messagebox.showwarning("警告", "请先选择一个模型")
            return
        
        index = self.model_listbox.curselection()[0]
        model_name = self.model_listbox.get(index)
        
        if messagebox.askyesno("确认", f"确定要删除模型 '{model_name}' 吗?"):
            self.config_manager.remove_model(model_name)
            self.load_models()
            messagebox.showinfo("成功", f"模型 '{model_name}' 已删除")
    
    def save_model(self):
        """保存模型配置"""
        name = self.name_var.get().strip()
        model_type = self.type_var.get().strip()
        api_key = self.key_var.get().strip()
        api_url = self.url_var.get().strip()
        
        if not name:
            messagebox.showwarning("警告", "模型名称不能为空")
            return
        
        if not model_type:
            messagebox.showwarning("警告", "请选择模型类型")
            return
        
        # 检查是否为更新现有模型
        existing_model = self.config_manager.get_model_by_name(name)
        
        # 创建模型配置
        model_config = {
            "name": name,
            "type": model_type,
            "key": api_key,
            "url": api_url
        }
        
        if existing_model:
            # 更新现有模型
            self.config_manager.update_model(name, model_config)
            messagebox.showinfo("成功", f"模型 '{name}' 已更新")
        else:
            # 添加新模型
            self.config_manager.add_model(model_config)
            messagebox.showinfo("成功", f"模型 '{name}' 已添加")
        
        # 重新加载模型列表
        self.load_models()

def open_model_settings(parent):
    """打开模型设置窗口"""
    settings_window = tk.Toplevel(parent)
    settings_window.title("模型设置")
    settings_window.geometry("600x400")
    settings_window.minsize(500, 300)
    
    # 创建模型设置界面
    ModelSettingsUI(settings_window)
    
    # 设置模态窗口
    settings_window.transient(parent)
    settings_window.grab_set()
    parent.wait_window(settings_window)