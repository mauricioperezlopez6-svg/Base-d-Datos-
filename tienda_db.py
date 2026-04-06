# tienda_db.py
import os
import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash, check_password_hash


class BaseDatosTienda:
    def __init__(self, ruta="./", bd="tienda.sqlite3"):
        self.bd_path = os.path.join(ruta, bd)
        self.con = None
        self.cursor = None
        self.conectar()
        self.crear_tablas()

    def conectar(self):
        try:
            self.con = sqlite3.connect(self.bd_path, check_same_thread=False)
            self.con.row_factory = sqlite3.Row
            self.cursor = self.con.cursor()
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.con.commit()
        except Error as e:
            print(f"[DB] Error al conectar: {e}")

    def cerrar(self):
        try:
            if self.con:
                self.con.close()
        except Error as e:
            print(f"[DB] Error al cerrar: {e}")

    def crear_tablas(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL UNIQUE,
                    contraseña TEXT NOT NULL,
                    email TEXT,
                    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS administradores(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL UNIQUE,
                    contraseña TEXT NOT NULL,
                    email TEXT,
                    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    precio REAL NOT NULL CHECK(precio >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0)
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedidos(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_nombre TEXT NOT NULL,
                    cliente_email TEXT,
                    total REAL NOT NULL CHECK(total >= 0),
                    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedido_items(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL CHECK(cantidad > 0),
                    precio_unit REAL NOT NULL CHECK(precio_unit >= 0),
                    FOREIGN KEY(pedido_id) REFERENCES pedidos(id)
                        ON DELETE CASCADE ON UPDATE CASCADE,
                    FOREIGN KEY(producto_id) REFERENCES productos(id)
                        ON DELETE RESTRICT ON UPDATE CASCADE
                );
            """)

            self.con.commit()
        except Error as e:
            print(f"[DB] Error creando tablas: {e}")

    # --------- Productos (CRUD) ----------
    def crear_producto(self, nombre, descripcion, precio, stock):
        try:
            self.cursor.execute("""
                INSERT INTO productos(nombre, descripcion, precio, stock)
                VALUES(?,?,?,?);
            """, (nombre.strip(), descripcion, float(precio), int(stock)))
            self.con.commit()
            return self.cursor.lastrowid
        except Error as e:
            print(f"[DB] No se pudo crear producto: {e}")
            return None

    def listar_productos(self):
        try:
            self.cursor.execute("SELECT * FROM productos ORDER BY id DESC;")
            return self.cursor.fetchall()
        except Error as e:
            print(f"[DB] Error listando productos: {e}")
            return []

    def obtener_producto(self, producto_id):
        try:
            self.cursor.execute("SELECT * FROM productos WHERE id=?;", (producto_id,))
            return self.cursor.fetchone()
        except Error as e:
            print(f"[DB] Error obteniendo producto: {e}")
            return None

    def actualizar_stock(self, producto_id, nuevo_stock):
        try:
            self.cursor.execute(
                "UPDATE productos SET stock=? WHERE id=?;",
                (int(nuevo_stock), producto_id)
            )
            self.con.commit()
            return self.cursor.rowcount > 0
        except Error as e:
            print(f"[DB] Error actualizando stock: {e}")
            return False

    # --------- Pedidos ----------
    def crear_pedido(self, cliente_nombre, cliente_email, items):
        """
        items: lista de dicts: [{"producto_id":1, "cantidad":2}, ...]
        - Calcula total
        - Valida stock
        - Descuenta stock
        - Inserta pedido + items en transacción
        """
        try:
            self.cursor.execute("BEGIN;")

            total = 0.0
            lineas = []

            for it in items:
                pid = int(it["producto_id"])
                qty = int(it["cantidad"])

                self.cursor.execute("SELECT id, precio, stock FROM productos WHERE id=?;", (pid,))
                p = self.cursor.fetchone()
                if not p:
                    raise ValueError(f"Producto {pid} no existe")
                if p["stock"] < qty:
                    raise ValueError(f"Stock insuficiente para producto {pid}")

                precio_unit = float(p["precio"])
                total += precio_unit * qty
                lineas.append((pid, qty, precio_unit))

            self.cursor.execute("""
                INSERT INTO pedidos(cliente_nombre, cliente_email, total)
                VALUES(?,?,?);
            """, (cliente_nombre.strip(), cliente_email, total))
            pedido_id = self.cursor.lastrowid

            for (pid, qty, precio_unit) in lineas:
                self.cursor.execute("""
                    INSERT INTO pedido_items(pedido_id, producto_id, cantidad, precio_unit)
                    VALUES(?,?,?,?);
                """, (pedido_id, pid, qty, precio_unit))

                # descontar stock
                self.cursor.execute("""
                    UPDATE productos SET stock = stock - ?
                    WHERE id=?;
                """, (qty, pid))

            self.con.commit()
            return pedido_id

        except Exception as e:
            self.con.rollback()
            print(f"[DB] Error creando pedido: {e}")
            return None

    def semilla_productos(self):
        """Crea productos de ejemplo si la tabla está vacía."""
        try:
            self.cursor.execute("SELECT COUNT(*) as c FROM productos;")
            c = self.cursor.fetchone()["c"]
            if c == 0:
                self.crear_producto("Playera", "Playera 100% algodón", 199.0, 20)
                self.crear_producto("Taza", "Taza cerámica 350ml", 129.0, 15)
                self.crear_producto("Sticker Pack", "Paquete de 10 stickers", 59.0, 50)
        except Error as e:
            print(f"[DB] Error semilla: {e}")

    # --------- Usuarios (Clientes) ----------
    def crear_usuario(self, usuario, contraseña, email=None):
        """Crea un nuevo usuario cliente."""
        try:
            contraseña_hash = generate_password_hash(contraseña)
            self.cursor.execute("""
                INSERT INTO usuarios(usuario, contraseña, email)
                VALUES(?,?,?);
            """, (usuario.strip(), contraseña_hash, email))
            self.con.commit()
            return self.cursor.lastrowid
        except Error as e:
            print(f"[DB] Error creando usuario: {e}")
            return None

    def validar_usuario_login(self, usuario, contraseña):
        """Valida credenciales de usuario cliente. Retorna el usuario si es válido."""
        try:
            self.cursor.execute("SELECT * FROM usuarios WHERE usuario=?;", (usuario.strip(),))
            u = self.cursor.fetchone()
            if u and check_password_hash(u["contraseña"], contraseña):
                return u
            return None
        except Error as e:
            print(f"[DB] Error validando usuario: {e}")
            return None

    def obtener_usuario_por_id(self, usuario_id):
        """Obtiene un usuario por ID."""
        try:
            self.cursor.execute("SELECT * FROM usuarios WHERE id=?;", (usuario_id,))
            return self.cursor.fetchone()
        except Error as e:
            print(f"[DB] Error obteniendo usuario: {e}")
            return None

    def usuario_existe(self, usuario):
        """Verifica si un usuario ya existe."""
        try:
            self.cursor.execute("SELECT COUNT(*) as c FROM usuarios WHERE usuario=?;", (usuario.strip(),))
            return self.cursor.fetchone()["c"] > 0
        except Error as e:
            print(f"[DB] Error verificando usuario: {e}")
            return False

    # --------- Administradores ----------
    def crear_administrador(self, usuario, contraseña, email=None):
        """Crea un nuevo administrador."""
        try:
            contraseña_hash = generate_password_hash(contraseña)
            self.cursor.execute("""
                INSERT INTO administradores(usuario, contraseña, email)
                VALUES(?,?,?);
            """, (usuario.strip(), contraseña_hash, email))
            self.con.commit()
            return self.cursor.lastrowid
        except Error as e:
            print(f"[DB] Error creando administrador: {e}")
            return None

    def validar_admin_login(self, usuario, contraseña):
        """Valida credenciales de administrador. Retorna el admin si es válido."""
        try:
            self.cursor.execute("SELECT * FROM administradores WHERE usuario=?;", (usuario.strip(),))
            a = self.cursor.fetchone()
            if a and check_password_hash(a["contraseña"], contraseña):
                return a
            return None
        except Error as e:
            print(f"[DB] Error validando admin: {e}")
            return None

    def obtener_admin_por_id(self, admin_id):
        """Obtiene un administrador por ID."""
        try:
            self.cursor.execute("SELECT * FROM administradores WHERE id=?;", (admin_id,))
            return self.cursor.fetchone()
        except Error as e:
            print(f"[DB] Error obteniendo admin: {e}")
            return None

    def admin_existe(self, usuario):
        """Verifica si un admin ya existe."""
        try:
            self.cursor.execute("SELECT COUNT(*) as c FROM administradores WHERE usuario=?;", (usuario.strip(),))
            return self.cursor.fetchone()["c"] > 0
        except Error as e:
            print(f"[DB] Error verificando admin: {e}")
            return False

    # --------- Productos: Eliminar ----------
    def eliminar_producto(self, producto_id):
        """Elimina un producto por su ID."""
        try:
            self.cursor.execute("DELETE FROM productos WHERE id=?;", (producto_id,))
            self.con.commit()
            return self.cursor.rowcount > 0
        except Error as e:
            print(f"[DB] Error eliminando producto: {e}")
            return False