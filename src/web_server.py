import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
from multiprocessing import Pool, cpu_count
import queue
import threading
import time
import json
import tempfile
import shutil

app = Flask(__name__)
socketio = SocketIO(app)

# Ubuntu系统无需设置Poppler路径
POPPLER_PATH = None

# Ubuntu系统的Tesseract配置
pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# 默认设置
DEFAULT_SETTINGS = {
    'quality': 'normal',  # low, normal, high
    'ocr_mode': 'auto',   # auto, force, skip
    'process_mode': 'multi',  # single, multi
    'thread_count': max(1, cpu_count() - 1)
}

# 全局转换状态
conversion_status = {
    'is_converting': False,
    'current_file': '',
    'total_files': 0,
    'current_index': 0,
    'total_progress': 0,
    'file_progress': 0
}

# 临时文件夹
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'pdf_to_md_temp')

def ensure_temp_dir():
    """确保临时目录存在"""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

def clean_temp_dir():
    """清理临时目录"""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    ensure_temp_dir()

def run_command(command):
    """运行系统命令并返回输出"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

@app.route('/api/select_file', methods=['GET'])
def select_file():
    """使用系统文件选择对话框选择文件"""
    try:
        # 使用zenity打开文件选择对话框
        cmd = 'zenity --file-selection --title="选择PDF文件" --file-filter="PDF文件 | *.pdf" --multiple'
        result = run_command(cmd)
        if result:
            files = result.split('|')
            return jsonify({'files': files})
        return jsonify({'error': '未选择文件'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/select_folder', methods=['GET'])
def select_folder():
    """使用系统文件夹选择对话框选择文件夹"""
    try:
        # 使用zenity打开文件夹选择对话框
        cmd = 'zenity --file-selection --title="选择文件夹" --directory'
        result = run_command(cmd)
        if result:
            # 查找文件夹中的所有PDF文件
            pdf_files = []
            for root, _, files in os.walk(result):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
            return jsonify({'folder': result, 'files': pdf_files})
        return jsonify({'error': '未选择文件夹'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/select_output', methods=['GET'])
def select_output():
    """使用系统文件夹选择对话框选择输出目录"""
    try:
        # 使用zenity打开文件夹选择对话框
        cmd = 'zenity --file-selection --title="选择输出目录" --directory'
        result = run_command(cmd)
        if result:
            return jsonify({'path': result})
        return jsonify({'error': '未选择目录'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_dependencies():
    """检查必要的依赖是否已安装"""
    errors = []
    try:
        import pdf2image
    except ImportError:
        errors.append("未找到pdf2image库，请运行: pip3 install pdf2image")
    
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        errors.append("未找到Tesseract-OCR，请运行: sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim")
    
    try:
        from pdf2image import convert_from_path
        convert_from_path("test.pdf", first_page=1, last_page=1)
    except Exception as e:
        if "poppler" in str(e).lower():
            errors.append("未找到poppler-utils，请运行: sudo apt-get install poppler-utils")
    
    return errors

def convert_pdf_page(args):
    """转换单个PDF页面"""
    image, quality, ocr_mode = args
    try:
        if quality == 'low':
            image = image.resize((int(image.width * 0.5), int(image.height * 0.5)))
        elif quality == 'high':
            pass
        else:  # normal
            if image.width > 1920 or image.height > 1080:
                image.thumbnail((1920, 1080))

        if ocr_mode == 'skip':
            text = ""
            if not text.strip():
                text = "无法提取文本，请启用OCR"
        else:
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')

        return text.strip()
    except Exception as e:
        return f"页面处理错误: {str(e)}"

def convert_pdf_to_md(pdf_path, output_dir, settings):
    """转换PDF到Markdown"""
    try:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{pdf_name}.md")

        socketio.emit('log', {'message': f"开始转换文件: {pdf_name}.pdf"})
        images = convert_from_path(pdf_path)
        socketio.emit('log', {'message': f"成功将PDF转换为{len(images)}页图片"})

        process_args = [(img, settings['quality'], settings['ocr_mode']) for img in images]

        if settings['process_mode'] == 'multi':
            socketio.emit('log', {'message': f"使用多进程模式 (进程数: {settings['thread_count']})"})
            with Pool(settings['thread_count']) as pool:
                results = pool.map(convert_pdf_page, process_args)
        else:
            socketio.emit('log', {'message': "使用单进程模式"})
            results = [convert_pdf_page(arg) for arg in process_args]

        socketio.emit('log', {'message': "正在生成Markdown文件..."})
        with open(output_path, 'w', encoding='utf-8') as md_file:
            for i, text in enumerate(results, 1):
                md_file.write(f"## 第 {i} 页\n\n")
                text = re.sub(r'\n\s*\n', '\n\n', text)
                text = re.sub(r'^(\d+\.\s+.*)$', r'### \1', text, flags=re.MULTILINE)
                text = re.sub(r'^[•\-\*]\s+(.*)$', r'- \1', text, flags=re.MULTILINE)
                md_file.write(text + '\n\n')

        socketio.emit('log', {'message': f"文件转换完成: {pdf_name}.pdf -> {pdf_name}.md"})
        return output_path
    except Exception as e:
        socketio.emit('log', {'message': f"转换过程中出现错误: {str(e)}"})
        return None

def process_conversion_queue(files, output_dir, settings):
    """处理转换队列"""
    global conversion_status
    
    try:
        conversion_status['total_files'] = len(files)
        conversion_status['current_index'] = 0
        conversion_status['is_converting'] = True
        
        for i, file in enumerate(files, 1):
            if not conversion_status['is_converting']:
                break
                
            conversion_status['current_file'] = os.path.basename(file)
            conversion_status['current_index'] = i
            conversion_status['total_progress'] = (i - 1) / len(files) * 100
            conversion_status['file_progress'] = 0
            socketio.emit('status_update', conversion_status)
            
            convert_pdf_to_md(file, output_dir, settings)
            conversion_status['file_progress'] = 100
            socketio.emit('status_update', conversion_status)
            
        conversion_status['is_converting'] = False
        conversion_status['total_progress'] = 100
        socketio.emit('status_update', conversion_status)
        socketio.emit('conversion_complete')
        
    except Exception as e:
        socketio.emit('log', {'message': f"转换过程中出现错误: {str(e)}"})
        conversion_status['is_converting'] = False
        socketio.emit('status_update', conversion_status)

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/check_dependencies')
def api_check_dependencies():
    """检查依赖"""
    errors = check_dependencies()
    return jsonify({'errors': errors})

@app.route('/api/start_conversion', methods=['POST'])
def api_start_conversion():
    """开始转换"""
    global conversion_status
    
    if conversion_status['is_converting']:
        return jsonify({'error': '转换正在进行中'}), 400
    
    try:
        # 清理临时目录
        clean_temp_dir()
        
        # 获取上传的文件
        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': '未选择文件'}), 400
            
        # 获取输出目录和设置
        output_dir = request.form.get('output_dir')
        if not output_dir:
            return jsonify({'error': '未选择输出目录'}), 400
            
        settings = json.loads(request.form.get('settings', '{}'))
        settings = {**DEFAULT_SETTINGS, **settings}
        
        # 保存上传的文件到临时目录
        pdf_paths = []
        for file in files:
            if file.filename.lower().endswith('.pdf'):
                temp_path = os.path.join(TEMP_DIR, file.filename)
                file.save(temp_path)
                pdf_paths.append(temp_path)
        
        if not pdf_paths:
            return jsonify({'error': '未找到有效的PDF文件'}), 400
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 启动转换线程
        threading.Thread(
            target=process_conversion_queue,
            args=(pdf_paths, output_dir, settings)
        ).start()
        
        return jsonify({'status': 'started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_conversion', methods=['POST'])
def api_stop_conversion():
    """停止转换"""
    global conversion_status
    conversion_status['is_converting'] = False
    return jsonify({'status': 'stopped'})

@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    socketio.emit('status_update', conversion_status)

if __name__ == '__main__':
    ensure_temp_dir()
    socketio.run(app, host='0.0.0.0', port=8080, debug=True) 