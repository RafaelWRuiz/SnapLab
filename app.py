from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import sqlite3
import subprocess
import secrets

# Configurações iniciais
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

# Garante que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Caminho do banco de dados (Render-friendly)
DB_PATH = os.environ.get('DB_PATH', 'database.db')

# Inicializa o banco de dados
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS registros (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome_animal TEXT,
                            especie TEXT,
                            tipo_amostra TEXT,
                            observacoes TEXT,
                            tipo_arquivo TEXT,
                            caminho TEXT,
                            data_hora TEXT
                        )''')

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('index'))

    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('index'))

    if arquivo and allowed_file(arquivo.filename):
        ext = arquivo.filename.rsplit('.', 1)[1].lower()
        tipo = 'video' if ext == 'mp4' else 'imagem'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_base = f"{timestamp}_{request.form['nome_animal']}_{request.form['tipo_amostra']}"
        filename = secure_filename(f"{nome_base}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        arquivo.save(filepath)

        if tipo == 'imagem':
            imagem = Image.open(filepath)
            imagem = imagem.resize((800, 600))
            imagem.save(filepath)
        elif tipo == 'video':
            novo_caminho = filepath.replace('.mp4', '_cut.mp4')
            subprocess.run(['ffmpeg', '-i', filepath, '-t', '2', '-c', 'copy', novo_caminho])
            os.remove(filepath)
            filepath = novo_caminho
            filename = os.path.basename(filepath)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''INSERT INTO registros 
                            (nome_animal, especie, tipo_amostra, observacoes, tipo_arquivo, caminho, data_hora)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (request.form['nome_animal'], request.form['especie'], request.form['tipo_amostra'],
                          request.form['observacoes'], tipo, filename, datetime.now().isoformat()))
        flash('Arquivo enviado com sucesso!')
        return redirect(url_for('index'))

    flash('Tipo de arquivo não permitido.')
    return redirect(url_for('index'))

@app.route('/galeria')
def galeria():
    with sqlite3.connect(DB_PATH) as conn:
        registros = conn.execute('SELECT * FROM registros ORDER BY data_hora DESC').fetchall()
    return render_template('galeria.html', registros=registros)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
