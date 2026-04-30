from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'refill_go_secret_key'

# --- LA SOLUCIÓN: RUTAS ABSOLUTAS ---
# Ubicamos exactamente dónde está este archivo app.py
basedir = os.path.abspath(os.path.dirname(__file__))

# Anclamos la carpeta static/img junto a app.py para que Flask nunca se pierda
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Si la carpeta no existe, la crea en el lugar correcto
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'tienda_v2.sqlite3')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_database():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL, pedidos INTEGER DEFAULT 0)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL, descripcion TEXT NOT NULL,
                    precio REAL NOT NULL, stock INTEGER NOT NULL, 
                    imagen TEXT, categoria TEXT NOT NULL)''')
    
    cursor = conn.execute('SELECT COUNT(*) FROM productos')
    if cursor.fetchone()[0] == 0:
        productos_refill = [
            ('Detergente Multiusos 1L', 'Fórmula biodegradable ideal para superficies y pisos.', 45.00, 100, 'detergente.jpg', 'limpieza'),
            ('Suavizante Ecológico 2L', 'Aroma lavanda. Libre de microplásticos.', 70.00, 50, 'suavizante.jpg', 'ropa'),
            ('Jabón Líquido Ropa 3L', 'Alto rendimiento para ropa blanca y de color.', 110.00, 30, 'jabon_liquido.jpg', 'ropa'),
            ('Lavatrastes Cítrico 1L', 'Corta la grasa al instante. Derivado de plantas.', 38.00, 80, 'lavatrastes.jpg', 'cocina'),
            ('Limpiador de Pisos 2L', 'Brillo intenso con aroma a bosque de Aguascalientes.', 65.00, 40, 'limpiador.jpg', 'limpieza'),
            ('Desinfectante Multiusos 1L', 'Elimina el 99.9% de bacterias y virus.', 55.00, 60, 'desinfectante.jpg', 'cocina')
        ]
        conn.executemany('INSERT INTO productos (nombre, descripcion, precio, stock, imagen, categoria) VALUES (?, ?, ?, ?, ?, ?)', productos_refill)
    
    conn.commit()
    conn.close()

inicializar_database()

@app.route('/')
def index():
    conn = get_db_connection()
    productos_db = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()
    
    productos_list = []
    for p in productos_db:
        precio_v = p['precio']
        precio_ant = None
        tag = None
        if 'pisos' in p['nombre'].lower() and p['precio'] == 65:
            precio_v, precio_ant, tag = 55.00, 65.00, 'oferta'
            
        productos_list.append({
            'id': p['id'], 'nombre': p['nombre'], 'desc': p['descripcion'],
            'precio': precio_v, 'precioOriginal': precio_ant,
            'imagen': p['imagen'] if p['imagen'] else 'default.jpg',
            'categoria': p['categoria'], 'tag': tag, 'emoji': '✨'
        })
    return render_template('index.html', productos_json=productos_list)

# --- SISTEMA DE CARRITO ---
@app.route('/agregar_carrito/<int:id>', methods=['POST'])
def agregar_carrito(id):
    if 'carrito' not in session:
        session['carrito'] = []
    
    carrito = session['carrito']
    carrito.append(id)
    session['carrito'] = carrito
    session.modified = True
    return redirect(url_for('carrito'))

@app.route('/carrito')
def carrito():
    if 'carrito' not in session:
        session['carrito'] = []
        
    conn = get_db_connection()
    productos_en_carrito = []
    total = 0.0
    
    if session['carrito']:
        para_buscar = ','.join('?' for _ in session['carrito'])
        query = f'SELECT * FROM productos WHERE id IN ({para_buscar})'
        productos_db = conn.execute(query, session['carrito']).fetchall()
        
        diccionario_prod = {p['id']: p for p in productos_db}
        for prod_id in session['carrito']:
            if prod_id in diccionario_prod:
                p = diccionario_prod[prod_id]
                precio_f = 55.0 if ('pisos' in p['nombre'].lower() and p['precio'] == 65) else p['precio']
                productos_en_carrito.append({'nombre': p['nombre'], 'precio': precio_f, 'imagen': p['imagen'], 'categoria': p['categoria']})
                total += precio_f
                
    conn.close()
    return render_template('carrito.html', productos=productos_en_carrito, total=total)

@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    session.pop('carrito', None)
    return redirect(url_for('carrito'))

# --- PANEL DE ADMINISTRACIÓN ---
@app.route('/admin', methods=('GET', 'POST'))
def admin():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if request.method == 'POST':
        if 'agregar' in request.form:
            precio = float(request.form['precio'])
            file = request.files.get('imagen_archivo')
            img_name = secure_filename(file.filename) if file and file.filename != '' else 'default.jpg'
            if file and file.filename != '': 
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
            
            conn.execute('INSERT INTO productos (nombre, descripcion, precio, stock, imagen, categoria) VALUES (?, ?, ?, ?, ?, ?)',
                         (request.form['nombre'], request.form['descripcion'], precio, int(request.form['stock']), img_name, request.form['categoria']))
            conn.commit()
        elif 'eliminar' in request.form:
            conn.execute('DELETE FROM productos WHERE id = ?', (request.form['id'],))
            conn.commit()
            
    productos = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()
    return render_template('admin.html', productos=productos, ventas=[{"total": 2450.50, "ordenes": 8}], avisos="Revisar stock en Aguascalientes")

# --- SISTEMA DE EDICIÓN DE PRODUCTOS ---
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        categoria = request.form['categoria']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])
        
        file = request.files.get('imagen_archivo')
        if file and file.filename != '':
            img_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
            conn.execute('UPDATE productos SET nombre = ?, descripcion = ?, precio = ?, stock = ?, imagen = ?, categoria = ? WHERE id = ?',
                         (nombre, descripcion, precio, stock, img_name, categoria, id))
        else:
            conn.execute('UPDATE productos SET nombre = ?, descripcion = ?, precio = ?, stock = ?, categoria = ? WHERE id = ?',
                         (nombre, descripcion, precio, stock, categoria, id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
        
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar.html', p=producto)

# --- USUARIOS Y SESIONES ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)', 
                         (request.form['nombre'], request.form['email'], request.form['password']))
            conn.commit()
            user = conn.execute('SELECT * FROM usuarios WHERE email = ?', (request.form['email'],)).fetchone()
            session['usuario_id'] = user['id']
            return redirect(url_for('perfil'))
        except: 
            return render_template('registro.html', error="El correo ya está registrado.")
        finally: 
            conn.close()
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (request.form['email'], request.form['password'])).fetchone()
        conn.close()
        if user:
            session['usuario_id'] = user['id']
            return redirect(url_for('perfil'))
    return render_template('login.html', error="Datos incorrectos")

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    conn.close()
    return render_template('cliente.html', usuario=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/nosotros')
def nosotros(): 
    return render_template('nosotros.html')

if __name__ == '__main__':
    app.run(debug=True)