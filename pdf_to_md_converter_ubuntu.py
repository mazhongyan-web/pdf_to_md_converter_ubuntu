#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import threading
import queue
import multiprocessing
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import time

class PDFConverter:
    def __init__(self):
        self.root = Tk()
        self.root.title("PDF转Markdown工具")
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 设置窗口大小和位置
        window_width = 800
        window_height = 600
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 初始化变量
        self.input_path = StringVar()
        self.output_path = StringVar()
        self.status_text = StringVar(value="就绪")
        self.progress_var = DoubleVar()
        self.quality_var = StringVar(value="normal")
        self.ocr_mode_var = StringVar(value="auto")
        self.process_mode_var = StringVar(value="multi")
        self.thread_count_var = StringVar(value="4")
        self.cancel_flag = False
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(N, W, E, S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 输入设置区域
        input_frame = ttk.LabelFrame(main_frame, text="输入设置", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(N, W, E, S), padx=5, pady=5)
        
        ttk.Button(input_frame, text="选择PDF文件", command=self.select_file).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(input_frame, text="选择文件夹", command=self.select_folder).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(input_frame, textvariable=self.input_path, wraplength=600).grid(row=1, column=0, columnspan=2, sticky=(W, E))
        
        # 输出设置区域
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="5")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(N, W, E, S), padx=5, pady=5)
        
        ttk.Button(output_frame, text="选择输出目录", command=self.select_output).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(output_frame, textvariable=self.output_path, wraplength=600).grid(row=1, column=0, sticky=(W, E))
        
        # 转换设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="转换设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(N, W, E, S), padx=5, pady=5)
        
        # 质量设置
        ttk.Label(settings_frame, text="转换质量:").grid(row=0, column=0, padx=5, pady=5)
        quality_combo = ttk.Combobox(settings_frame, textvariable=self.quality_var, values=["low", "normal", "high"], state="readonly")
        quality_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # OCR模式设置
        ttk.Label(settings_frame, text="OCR模式:").grid(row=0, column=2, padx=5, pady=5)
        ocr_combo = ttk.Combobox(settings_frame, textvariable=self.ocr_mode_var, values=["auto", "force", "skip"], state="readonly")
        ocr_combo.grid(row=0, column=3, padx=5, pady=5)
        
        # 处理模式设置
        ttk.Label(settings_frame, text="处理模式:").grid(row=1, column=0, padx=5, pady=5)
        process_combo = ttk.Combobox(settings_frame, textvariable=self.process_mode_var, values=["single", "multi"], state="readonly")
        process_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # 线程数设置
        ttk.Label(settings_frame, text="线程数:").grid(row=1, column=2, padx=5, pady=5)
        thread_combo = ttk.Combobox(settings_frame, textvariable=self.thread_count_var, values=["1", "2", "4", "8"], state="readonly")
        thread_combo.grid(row=1, column=3, padx=5, pady=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="转换进度", padding="5")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(N, W, E, S), padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(W, E), padx=5, pady=5)
        
        ttk.Label(progress_frame, textvariable=self.status_text).grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=(E, W), padx=5, pady=5)
        button_frame.columnconfigure(1, weight=1)
        
        self.start_button = ttk.Button(button_frame, text="开始转换", command=self.start_conversion)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="取消转换", command=self.cancel_conversion, state=DISABLED)
        self.cancel_button.grid(row=0, column=1, padx=5)
        
    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF文件", "*.pdf")])
        if file_path:
            self.input_path.set(file_path)
            
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.input_path.set(folder_path)
            
    def select_output(self):
        output_path = filedialog.askdirectory()
        if output_path:
            self.output_path.set(output_path)
            
    def get_quality_dpi(self):
        quality_map = {
            "low": 150,
            "normal": 300,
            "high": 600
        }
        return quality_map.get(self.quality_var.get(), 300)
        
    def convert_pdf_page(self, pdf_path, page_num, dpi):
        try:
            images = convert_from_path(pdf_path, dpi=dpi, first_page=page_num+1, last_page=page_num+1)
            if not images:
                return ""
                
            image = images[0]
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text.strip()
        except Exception as e:
            print(f"Error converting page {page_num}: {str(e)}")
            return ""
            
    def convert_pdf_to_md(self, pdf_path, output_path):
        try:
            # 获取PDF页数
            images = convert_from_path(pdf_path, dpi=72, first_page=1, last_page=1)
            if not images:
                return False
                
            # 创建输出文件
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            md_path = os.path.join(output_path, f"{pdf_name}.md")
            
            # 获取质量设置
            dpi = self.get_quality_dpi()
            
            # 转换设置
            is_multi = self.process_mode_var.get() == "multi"
            thread_count = int(self.thread_count_var.get()) if is_multi else 1
            
            # 创建线程池
            with multiprocessing.Pool(processes=thread_count) as pool:
                results = []
                for page_num in range(len(images)):
                    if self.cancel_flag:
                        return False
                    result = pool.apply_async(self.convert_pdf_page, (pdf_path, page_num, dpi))
                    results.append(result)
                    
                # 等待所有页面转换完成
                texts = []
                for i, result in enumerate(results):
                    if self.cancel_flag:
                        return False
                    text = result.get()
                    texts.append(text)
                    self.progress_var.set((i + 1) * 100 / len(results))
                    self.root.update()
                    
            # 写入Markdown文件
            with open(md_path, 'w', encoding='utf-8') as f:
                for i, text in enumerate(texts):
                    if text:
                        f.write(f"## 第{i+1}页\n\n{text}\n\n")
                        
            return True
        except Exception as e:
            print(f"Error converting PDF: {str(e)}")
            return False
            
    def process_files(self):
        try:
            input_path = self.input_path.get()
            output_path = self.output_path.get()
            
            if not input_path or not output_path:
                messagebox.showerror("错误", "请选择输入和输出路径")
                return
                
            # 确保输出目录存在
            os.makedirs(output_path, exist_ok=True)
            
            # 获取所有PDF文件
            pdf_files = []
            if os.path.isfile(input_path):
                if input_path.lower().endswith('.pdf'):
                    pdf_files.append(input_path)
            else:
                for root, _, files in os.walk(input_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_files.append(os.path.join(root, file))
                            
            if not pdf_files:
                messagebox.showinfo("提示", "未找到PDF文件")
                return
                
            # 转换所有文件
            for i, pdf_file in enumerate(pdf_files):
                if self.cancel_flag:
                    break
                    
                self.status_text.set(f"正在转换: {os.path.basename(pdf_file)}")
                success = self.convert_pdf_to_md(pdf_file, output_path)
                
                if not success and not self.cancel_flag:
                    messagebox.showerror("错误", f"转换失败: {os.path.basename(pdf_file)}")
                    
            if not self.cancel_flag:
                messagebox.showinfo("完成", "所有文件转换完成")
                
        except Exception as e:
            messagebox.showerror("错误", f"转换过程出错: {str(e)}")
        finally:
            self.status_text.set("就绪")
            self.progress_var.set(0)
            self.start_button.config(state=NORMAL)
            self.cancel_button.config(state=DISABLED)
            self.cancel_flag = False
            
    def start_conversion(self):
        self.cancel_flag = False
        self.start_button.config(state=DISABLED)
        self.cancel_button.config(state=NORMAL)
        threading.Thread(target=self.process_files, daemon=True).start()
        
    def cancel_conversion(self):
        self.cancel_flag = True
        self.status_text.set("正在取消...")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PDFConverter()
    app.run() 