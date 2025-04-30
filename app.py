from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import json
import multiprocessing
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import threading
import queue
import time
import shutil

app = Flask(__name__)
socketio = SocketIO(app)

# 全局变量
conversion_status = {
    'is_converting': False,
    'total_progress': 0,
    'file_progress': 0,
    'current_file': None,
    'stop_requested': False
}

# 转换设置
conversion_settings = {
    'quality': 'normal',
    'ocr_mode': 'auto',
    'process_mode': 'multi',
    'thread_count': 4
}

def update_status(total_progress=None, file_progress=None, current_file=None):
    """更新并发送状态到前端"""
    if total_progress is not None:
        conversion_status['total_progress'] = total_progress
    if file_progress is not None:
        conversion_status['file_progress'] = file_progress
    if current_file is not None:
        conversion_status['current_file'] = current_file
    
    socketio.emit('status_update', conversion_status)

def emit_log(message):
    """发送日志消息到前端"""
    socketio.emit('log', {'message': message})

def convert_pdf_page(page, quality):
    """转换单个PDF页面为文本"""
    try:
        # 根据质量设置调整DPI
        dpi = {
            'low': 150,
            'normal': 300,
            'high': 600
        }.get(quality, 300)
        
        # OCR识别
        text = pytesseract.image_to_string(page, lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        emit_log(f"页面转换错误: {str(e)}")
        return ""

def convert_pdf_to_md(pdf_path, output_dir, settings):
    """转换单个PDF文件为Markdown"""
    try:
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.md")
        
        # 转换PDF为图片
        emit_log(f"正在处理文件: {base_name}")
        pages = convert_from_path(pdf_path)
        total_pages = len(pages)
        
        # 创建进程池
        if settings['process_mode'] == 'multi':
            pool = multiprocessing.Pool(processes=settings['thread_count'])
        
        # 转换每一页
        all_text = []
        for i, page in enumerate(pages):
            if conversion_status['stop_requested']:
                raise Exception("转换已被用户停止")
            
            # 更新进度
            file_progress = (i + 1) / total_pages * 100
            update_status(file_progress=file_progress)
            
            # 根据处理模式选择转换方法
            if settings['process_mode'] == 'multi':
                text = pool.apply(convert_pdf_page, (page, settings['quality']))
            else:
                text = convert_pdf_page(page, settings['quality'])
            
            all_text.append(text)
        
        if settings['process_mode'] == 'multi':
            pool.close()
            pool.join()
        
        # 写入Markdown文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name}\n\n")
            for i, text in enumerate(all_text):
                f.write(f"## 第 {i+1} 页\n\n{text}\n\n")
        
        emit_log(f"文件转换完成: {base_name}")
        return True
    except Exception as e:
        emit_log(f"文件转换失败 {base_name}: {str(e)}")
        return False
    finally:
        if 'pool' in locals():
            pool.terminate()

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/check_dependencies')
def check_dependencies():
    """检查系统依赖"""
    errors = []
    
    # 检查tesseract
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        errors.append("未检测到Tesseract-OCR，请确保已正确安装")
    
    # 检查poppler
    if not shutil.which('pdftoppm'):
        errors.append("未检测到Poppler-utils，请确保已正确安装")
    
    # 检查中文语言包
    try:
        if 'chi_sim' not in pytesseract.get_languages():
            errors.append("未检测到Tesseract中文语言包，请安装chi_sim语言包")
    except Exception:
        errors.append("无法检查Tesseract语言包")
    
    return jsonify({'errors': errors})

@app.route('/api/start_conversion', methods=['POST'])
def start_conversion():
    """开始转换过程"""
    if conversion_status['is_converting']:
        return jsonify({'error': '转换已在进行中'}), 400
    
    try:
        files = request.files.getlist('files[]')
        output_dir = request.form.get('output_dir')
        settings = json.loads(request.form.get('settings'))
        
        if not files:
            return jsonify({'error': '未选择文件'}), 400
        if not output_dir:
            return jsonify({'error': '未选择输出目录'}), 400
        
        # 更新转换设置
        conversion_settings.update(settings)
        
        # 重置状态
        conversion_status['is_converting'] = True
        conversion_status['stop_requested'] = False
        conversion_status['total_progress'] = 0
        conversion_status['file_progress'] = 0
        
        def conversion_thread():
            try:
                total_files = len(files)
                for i, file in enumerate(files):
                    if conversion_status['stop_requested']:
                        break
                    
                    # 保存临时文件
                    temp_path = os.path.join(output_dir, file.filename)
                    file.save(temp_path)
                    
                    # 更新状态
                    conversion_status['current_file'] = file.filename
                    update_status(total_progress=(i / total_files * 100))
                    
                    # 转换文件
                    success = convert_pdf_to_md(temp_path, output_dir, conversion_settings)
                    
                    # 删除临时文件
                    os.remove(temp_path)
                    
                    if not success and not conversion_status['stop_requested']:
                        emit_log(f"警告: {file.filename} 转换失败")
                
                # 完成转换
                conversion_status['is_converting'] = False
                conversion_status['current_file'] = None
                update_status(total_progress=100, file_progress=100)
                socketio.emit('conversion_complete')
                emit_log("所有文件转换完成")
            
            except Exception as e:
                conversion_status['is_converting'] = False
                emit_log(f"转换过程出错: {str(e)}")
                socketio.emit('conversion_complete')
        
        # 启动转换线程
        thread = threading.Thread(target=conversion_thread)
        thread.start()
        
        return jsonify({'message': '转换已开始'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_conversion', methods=['POST'])
def stop_conversion():
    """停止转换过程"""
    if not conversion_status['is_converting']:
        return jsonify({'error': '没有正在进行的转换'}), 400
    
    conversion_status['stop_requested'] = True
    emit_log("正在停止转换...")
    return jsonify({'message': '已发送停止请求'})

if __name__ == '__main__':
    socketio.run(app, debug=True) 