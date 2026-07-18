import os
import random
import string
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# サイト全体のログインパスワード
SITE_PASSWORD = "102464115"

# 生成されたキーと詳細情報の対応を保存する辞書
# 構造例: { "key": { "files": [...], "password": "...", "allowed_emails": [...] } }
db = {}

def generate_unique_key(length=20):
    characters = string.ascii_letters + string.digits
    while True:
        key = ''.join(random.choices(characters, k=length))
        if key not in db:
            return key

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "healthy", "message": "File Sharing API is running"}), 200

# サイトログイン用エンドポイント
@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    password = data.get('password')
    if password == SITE_PASSWORD:
        return jsonify({"success": True}), 200
    return jsonify({"error": "パスワードが正しくありません"}), 401

# ファイルアップロード処理（セキュリティ情報追加）
@app.route('/upload', methods=['POST'])
def upload_files():
    # 簡易ログインチェック（簡易的にヘッダーやフォーム等でパスワードを検証）
    site_password = request.form.get('site_password')
    if site_password != SITE_PASSWORD:
        return jsonify({"error": "認証エラー: サイトのパスワードが不正です"}), 401

    if 'files' not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400

    # 許可するメールアドレスの処理
    allowed_emails_raw = request.form.get('allowed_emails', '')
    # 空白、カンマ、改行などで区切られたメールアドレスをリスト化
    allowed_emails = [e.strip() for e in allowed_emails_raw.replace(',', ' ').split() if e.strip()]
    if not allowed_emails:
        allowed_emails = ['all'] # 全員許可

    # ダウンロード用20桁パスワードの自動生成
    download_password = generate_unique_key(20)
    key = generate_unique_key(20)
    saved_files = []

    key_folder = os.path.join(app.config['UPLOAD_FOLDER'], key)
    os.makedirs(key_folder, exist_ok=True)

    for file in files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(key_folder, filename)
        file.save(file_path)
        saved_files.append(filename)

    # 拡張したデータベース構造に保存
    db[key] = {
        "files": saved_files,
        "password": download_password,
        "allowed_emails": allowed_emails
    }

    return jsonify({
        "key": key, 
        "password": download_password, 
        "files": saved_files,
        "allowed_emails": allowed_emails
    }), 200

# キーとパスワード、メールアドレスに紐づくファイル一覧の取得
@app.route('/files/<key>', methods=['POST'])
def get_files(key):
    data = request.json or {}
    password = data.get('password')
    email = data.get('email', '').strip()

    if key not in db:
        return jsonify({"error": "指定されたキーが見つかりません"}), 404
    
    # 20桁パスワードの検証
    if db[key]['password'] != password:
        return jsonify({"error": "キーまたはパスワードが正しくありません"}), 401

    # Gmailアカウントの検証
    allowed = db[key]['allowed_emails']
    if 'all' not in allowed and email not in allowed:
        return jsonify({"error": "このアカウントにはダウンロード権限がありません"}), 403

    return jsonify({"key": key, "files": db[key]['files']}), 200

# ファイルのダウンロード（ダウンロード時も認証チェックを行う）
@app.route('/download/<key>/<filename>', methods=['POST'])
def download_file(key, filename):
    data = request.json or {}
    password = data.get('password')
    email = data.get('email', '').strip()

    if key not in db or filename not in db[key]['files']:
        return jsonify({"error": "ファイルが見つかりません"}), 404
    
    if db[key]['password'] != password:
        return jsonify({"error": "認証エラー"}), 401

    allowed = db[key]['allowed_emails']
    if 'all' not in allowed and email not in allowed:
        return jsonify({"error": "権限エラー"}), 403
    
    key_folder = os.path.join(app.config['UPLOAD_FOLDER'], key)
    return send_from_directory(key_folder, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
