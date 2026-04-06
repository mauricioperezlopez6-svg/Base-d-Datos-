# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from tienda_db import BaseDatosTienda
from functools import wraps

app = Flask(__name__)
app.secret_key = "cambia-esto-por-algo-seguro"

db = BaseDatosTienda(ruta="./", bd="tienda.sqlite3")
db.semilla_productos()

def carrito_session():
    # carrito: { "producto_id": cantidad }
    if "carrito" not in session:
        session["carrito"] = {}
    return session["carrito"]

def usuario_requerido(f):
    """Decorador para proteger rutas que requieren usuario autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión primero.")
            return redirect(url_for("login_usuario"))
        return f(*args, **kwargs)
    return decorated_function

def admin_requerido(f):
    """Decorador para proteger rutas que requieren admin autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            flash("Debes iniciar sesión como administrador.")
            return redirect(url_for("login_admin"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    productos = db.listar_productos()
    return render_template("index.html", productos=productos, carrito=carrito_session())

@app.route("/producto/<int:producto_id>")
def producto(producto_id):
    p = db.obtener_producto(producto_id)
    if not p:
        return "Producto no encontrado", 404
    return render_template("producto.html", p=p, carrito=carrito_session())

@app.route("/carrito/agregar", methods=["POST"])
def carrito_agregar():
    pid = request.form.get("producto_id", type=int)
    qty = request.form.get("cantidad", type=int, default=1)

    p = db.obtener_producto(pid)
    if not p:
        flash("Producto no existe.")
        return redirect(url_for("index"))

    cart = carrito_session()
    cart[str(pid)] = int(cart.get(str(pid), 0)) + max(qty, 1)
    session["carrito"] = cart
    flash("Agregado al carrito.")
    return redirect(request.referrer or url_for("index"))

@app.route("/carrito")
def carrito():
    cart = carrito_session()
    items = []
    total = 0.0

    for pid_str, qty in cart.items():
        p = db.obtener_producto(int(pid_str))
        if not p:
            continue
        subtotal = float(p["precio"]) * int(qty)
        total += subtotal
        items.append({"p": p, "qty": int(qty), "subtotal": subtotal})

    return render_template("carrito.html", items=items, total=total)

@app.route("/carrito/quitar", methods=["POST"])
def carrito_quitar():
    pid = request.form.get("producto_id", type=int)
    cart = carrito_session()
    cart.pop(str(pid), None)
    session["carrito"] = cart
    return redirect(url_for("carrito"))

@app.route("/checkout", methods=["POST"])
def checkout():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip() or None

    if not nombre:
        flash("Escribe tu nombre para continuar.")
        return redirect(url_for("carrito"))

    cart = carrito_session()
    if not cart:
        flash("Tu carrito está vacío.")
        return redirect(url_for("index"))

    items = [{"producto_id": int(pid), "cantidad": int(qty)} for pid, qty in cart.items()]

    pedido_id = db.crear_pedido(nombre, email, items)
    if not pedido_id:
        flash("No se pudo procesar el pedido (¿stock insuficiente?).")
        return redirect(url_for("carrito"))

    session["carrito"] = {}
    return render_template("checkout_ok.html", pedido_id=pedido_id)

@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
def agregar_producto():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio = request.form.get("precio", type=float)
        stock = request.form.get("stock", type=int, default=0)

        if not nombre or precio is None:
            flash("El nombre y precio son obligatorios.")
            return redirect(url_for("agregar_producto"))

        producto_id = db.crear_producto(nombre, descripcion, precio, stock)
        if producto_id:
            flash(f"Producto '{nombre}' agregado exitosamente.")
            return redirect(url_for("index"))
        else:
            flash("Error al crear el producto.")
            return redirect(url_for("agregar_producto"))

    return render_template("agregar_producto.html")

# --------- USUARIOS (Clientes) ---------
@app.route("/registro", methods=["GET", "POST"])
def registro_usuario():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contraseña = request.form.get("contraseña", "").strip()
        email = request.form.get("email", "").strip() or None

        if not usuario or not contraseña:
            flash("Usuario y contraseña son requeridos.")
            return redirect(url_for("registro_usuario"))

        if db.usuario_existe(usuario):
            flash("El usuario ya existe.")
            return redirect(url_for("registro_usuario"))

        usuario_id = db.crear_usuario(usuario, contraseña, email)
        if usuario_id:
            flash("Registrado exitosamente. Inicia sesión.")
            return redirect(url_for("login_usuario"))
        else:
            flash("Error al registrar.")
            return redirect(url_for("registro_usuario"))

    return render_template("registro_usuario.html")

@app.route("/login", methods=["GET", "POST"])
def login_usuario():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contraseña = request.form.get("contraseña", "").strip()

        u = db.validar_usuario_login(usuario, contraseña)
        if u:
            session["usuario_id"] = u["id"]
            session["usuario_nombre"] = u["usuario"]
            flash(f"Bienvenido {u['usuario']}!")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos.")
            return redirect(url_for("login_usuario"))

    return render_template("login_usuario.html")

@app.route("/logout")
def logout_usuario():
    session.pop("usuario_id", None)
    session.pop("usuario_nombre", None)
    flash("Sesión cerrada.")
    return redirect(url_for("index"))

# --------- ADMINISTRADORES ---------
@app.route("/admin/login", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contraseña = request.form.get("contraseña", "").strip()

        a = db.validar_admin_login(usuario, contraseña)
        if a:
            session["admin_id"] = a["id"]
            session["admin_nombre"] = a["usuario"]
            flash(f"¡Bienvenido administrador {a['usuario']}!")
            return redirect(url_for("admin_panel"))
        else:
            flash("Usuario o contraseña de admin incorrectos.")
            return redirect(url_for("login_admin"))

    return render_template("login_admin.html")

@app.route("/admin/setup", methods=["GET", "POST"])
def admin_setup():
    """Crear el primer administrador (solo disponible si no hay admin)"""
    try:
        db.cursor.execute("SELECT COUNT(*) as c FROM administradores;")
        admin_count = db.cursor.fetchone()["c"]
    except:
        admin_count = 0
    
    if admin_count > 0:
        flash("Ya existe un administrador registrado.")
        return redirect(url_for("login_admin"))
    
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contraseña = request.form.get("contraseña", "").strip()
        email = request.form.get("email", "").strip() or None

        if not usuario or not contraseña or len(contraseña) < 6:
            flash("Usuario requerido y contraseña mínimo 6 caracteres.")
            return redirect(url_for("admin_setup"))

        admin_id = db.crear_administrador(usuario, contraseña, email)
        if admin_id:
            flash(f"Administrador '{usuario}' creado. Ahora inicia sesión.")
            return redirect(url_for("login_admin"))
        else:
            flash("Error al crear administrador.")
            return redirect(url_for("admin_setup"))

    return render_template("admin_setup.html")

@app.route("/admin/logout")
def logout_admin():
    session.pop("admin_id", None)
    session.pop("admin_nombre", None)
    flash("Sesión de admin cerrada.")
    return redirect(url_for("index"))

@app.route("/admin/panel")
@admin_requerido
def admin_panel():
    productos = db.listar_productos()
    return render_template("admin_panel.html", productos=productos)

@app.route("/admin/productos/agregar", methods=["GET", "POST"])
@admin_requerido
def admin_agregar_producto():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio = request.form.get("precio", type=float)
        stock = request.form.get("stock", type=int, default=0)

        if not nombre or precio is None:
            flash("El nombre y precio son obligatorios.")
            return redirect(url_for("admin_agregar_producto"))

        producto_id = db.crear_producto(nombre, descripcion, precio, stock)
        if producto_id:
            flash(f"Producto '{nombre}' agregado exitosamente.")
            return redirect(url_for("admin_panel"))
        else:
            flash("Error al crear el producto.")
            return redirect(url_for("admin_agregar_producto"))

    return render_template("admin_agregar_producto.html")

@app.route("/admin/productos/eliminar/<int:producto_id>", methods=["POST"])
@admin_requerido
def admin_eliminar_producto(producto_id):
    p = db.obtener_producto(producto_id)
    if not p:
        flash("Producto no encontrado.")
        return redirect(url_for("admin_panel"))

    if db.eliminar_producto(producto_id):
        flash(f"Producto '{p['nombre']}' eliminado exitosamente.")
    else:
        flash("Error al eliminar producto.")
    
    return redirect(url_for("admin_panel"))

if __name__ == "__main__":
    app.run(debug=True)


    '''
    Instrucciones de ejecucion 
    
    ejecutar en terminal: pip install flask werkzeug
    ejecutar en terminal: py app.py
    abrir en la web: http://127.0.0.1:5000/
    '''