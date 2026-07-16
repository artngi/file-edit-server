import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
# すべてのオリジンからのリクエストを許可（HTMLを別リポジトリで動かすため）
CORS(app)

# アップロードされたファイルを保存するフォルダ
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 生成されたキーとファイル名の対応を保存する辞書 (メモリ上に保存)
# ※Renderの無料インスタンスが再起動するとリセットされます
db = {}

def generate_unique_key():
    characters = string.ascii_letters + string.digits
    while True:
        # 20桁のランダムな文字列を生成
        key = ''.join(random.choices(characters, k=20))
        if key not in db:
            return key

# ルートパスでのNotFoundを防ぐための生存確認用
@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "healthy", "message": "File Sharing API is running"}), 200

# ファイルアップロード処理
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400

    key = generate_unique_key()
    saved_files = []

    # キー専用のサブフォルダを作成して重複を避ける
    key_folder = os.path.join(app.config['UPLOAD_FOLDER'], key)
    os.makedirs(key_folder, exist_ok=True)

    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(key_folder, filename)
        file.save(file_path)
        saved_files.append(filename)

    # データベース（メモリ）に記録
    db[key] = saved_files

    return jsonify({"key": key, "files": saved_files}), 200

# キーに紐づくファイル一覧の取得
@app.route('/files/<key>', methods=['GET'])
def get_files(key):
    if key not in db:
        return jsonify({"error": "指定されたキーが見つかりません"}), 404
    return jsonify({"key": key, "files": db[key]}), 200

# ファイルのダウンロード
@app.route('/download/<key>/<filename>', methods=['GET'])
def download_file(key, filename):
    if key not in db or filename not in db[key]:
        return jsonify({"error": "ファイルが見つかりません"}), 404
    
    key_folder = os.path.join(app.config['UPLOAD_FOLDER'], key)
    return send_from_directory(key_folder, filename, as_attachment=True)

if __name__ == '__main__':
    # Render環境のポートに対応
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
