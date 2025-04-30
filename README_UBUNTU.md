# PDF转Markdown工具 - Ubuntu版

这是一个用于将PDF文件转换为Markdown格式的工具，专门针对Ubuntu系统优化。

## 功能特点

- 支持批量转换PDF文件
- 支持文件夹批量导入
- 自定义输出目录
- 实时转换进度显示
- 多线程处理支持
- 可调节转换质量
- 支持中英文OCR识别
- 友好的图形界面

## 系统要求

- Ubuntu 18.04 或更高版本
- Python 3.8 或更高版本
- 系统管理员权限（用于安装依赖）

## 安装步骤

1. 安装系统依赖：
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-tk tesseract-ocr tesseract-ocr-chi-sim poppler-utils
```

2. 克隆或下载本项目到本地。

3. 进入项目目录，安装Python依赖：
```bash
pip3 install -r requirements.txt
```

## 使用说明

1. 启动程序：
```bash
python3 pdf_to_md_converter_ubuntu.py
```

2. 程序界面分为四个主要区域：

   - **输入设置**：选择要转换的PDF文件或文件夹
   - **输出设置**：选择转换后的Markdown文件保存位置
   - **转换设置**：调整转换参数
     - 转换质量：low（低）/ normal（中）/ high（高）
     - OCR模式：auto（自动）/ force（强制）/ skip（跳过）
     - 处理模式：single（单线程）/ multi（多线程）
     - 线程数：可选择1至CPU核心数
   - **转换进度**：显示当前转换进度和状态

3. 操作步骤：

   1. 点击"选择PDF文件"或"选择文件夹"按钮选择要转换的文件
   2. 点击"选择输出目录"按钮选择保存位置
   3. 根据需要调整转换设置
   4. 点击"开始转换"按钮开始处理
   5. 等待转换完成

## 注意事项

1. 首次运行时请确保已正确安装所有依赖。
2. 对于大文件，转换时间可能较长，请耐心等待。
3. 转换质量设置会影响处理速度：
   - low：速度最快，质量较低
   - normal：平衡速度和质量
   - high：最高质量，速度较慢
4. 如果遇到中文识别问题，请确保已正确安装中文语言包。

## 常见问题

1. 如果遇到权限错误：
```bash
sudo chmod +x pdf_to_md_converter_ubuntu.py
```

2. 如果遇到Tesseract错误，请确认安装：
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
```

3. 如果遇到PDF处理错误，请确认安装：
```bash
sudo apt-get install poppler-utils
```

## 性能优化建议

1. 对于大量文件的批处理，建议使用多线程模式。
2. 如果不需要高精度识别，可以选择low质量以提高速度。
3. 确保系统有足够的内存和CPU资源。

## 技术支持

如果遇到问题，请检查：
1. 系统依赖是否完整安装
2. Python版本是否满足要求
3. 是否有足够的磁盘空间
4. 是否有正确的文件访问权限 