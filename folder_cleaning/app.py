import os
import shutil
import zipfile
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# 파일이 임시로 저장되어 정리될 서버 내부 공간
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'web_sorting_zone')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 1단계: 확장자 기반 자동 분류 규칙
AUTO_RULES = {
    '.ppt': 'PPT_정리', '.pptx': 'PPT_정리',
    '.hwp': '한컴_정리', '.hwpx': '한컴_정리'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """ 사용자가 올린 파일들을 받아 1단계 자동 분류 진행 """
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "파일이 없습니다."})
    
    uploaded_files = request.files.getlist('files')
    
    # 매번 깨끗한 정리를 위해 기존 임시 폴더 삭제 후 재생성
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    remaining_files = []
    
    for file in uploaded_files:
        if file.filename == '':
            continue
            
        ext = os.path.splitext(file.filename)[1].lower()
        
        if ext in AUTO_RULES:
            # PPT, HWP는 지정된 폴더로 자동 이동
            target_dir = os.path.join(UPLOAD_FOLDER, AUTO_RULES[ext])
            os.makedirs(target_dir, exist_ok=True)
            file.save(os.path.join(target_dir, file.filename))
        else:
            # 수동 분류해야 할 파일들은 unclassified 폴더에 임시 보관
            unclassified_dir = os.path.join(UPLOAD_FOLDER, '미분류_파일')
            os.makedirs(unclassified_dir, exist_ok=True)
            file.save(os.path.join(unclassified_dir, file.filename))
            remaining_files.append(file.filename)
            
    return jsonify({"status": "success", "remaining": remaining_files})

@app.route('/move-file', methods=['POST'])
def move_file():
    """ 2단계: 사용자가 화면에서 지정한 폴더로 파일 이동 """
    data = request.json
    file_name = data.get('file_name')
    target_folder = data.get('target_folder').strip()
    
    src_path = os.path.join(UPLOAD_FOLDER, '미분류_파일', file_name)
    dest_dir = os.path.join(UPLOAD_FOLDER, target_folder)
    
    if os.path.exists(src_path) and target_folder:
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(src_path, os.path.join(dest_dir, file_name))
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "이동 실패"})

@app.route('/download-zip', methods=['GET'])
def download_zip():
    """ 모든 정리가 끝난 폴더 구조를 압축해서 다운로드 """
    zip_path = os.path.join(os.getcwd(), '정리완료_파일.zip')
    
    # 미분류 폴더가 비어있지 않다면 그것도 포함해서 압축, 비어있으면 삭제
    unclassified_dir = os.path.join(UPLOAD_FOLDER, '미분류_파일')
    if os.path.exists(unclassified_dir) and not os.listdir(unclassified_dir):
        os.rmdir(unclassified_dir)
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                # 정제된 폴더 트리 구조 유지하며 압축
                arcname = os.path.relpath(file_path, UPLOAD_FOLDER)
                zipf.write(file_path, arcname)
                
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
