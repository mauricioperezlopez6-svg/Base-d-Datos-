#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el sistema de autenticación
"""

import sqlite3
import os
from tienda_db import BaseDatosTienda

print("=" * 60)
print("DIAGNÓSTICO DE LA TIENDA")
print("=" * 60)

# 1. Verificar dependencias
print("\n📦 Verificando dependencias...")
try:
    import flask
    print("  ✓ Flask instalado")
except ImportError:
    print("  ✗ Flask NO instalado - Ejecuta: pip install flask")

try:
    import werkzeug
    print("  ✓ Werkzeug instalado")
except ImportError:
    print("  ✗ Werkzeug NO instalado - Ejecuta: pip install werkzeug")

# 2. Verificar base de datos
print("\n📁 Verificando base de datos...")
db = BaseDatosTienda(ruta="./", bd="tienda.sqlite3")

# Contar administradores
db.cursor.execute("SELECT COUNT(*) as c FROM administradores;")
admin_count = db.cursor.fetchone()["c"]
print(f"  Administradores en BD: {admin_count}")

if admin_count == 0:
    print("\n  ⚠️  NO HAY ADMINISTRADORES REGISTRADOS")
    print("  📝 Pasos para crear un administrador:")
    print("     1. Abre http://127.0.0.1:5000/admin/setup")
    print("     2. Completa el formulario con usuario y contraseña")
    print("     3. Click en 'Crear Administrador'")
else:
    print("\n  Administradores registrados:")
    db.cursor.execute("SELECT id, usuario, email FROM administradores;")
    admins = db.cursor.fetchall()
    for admin in admins:
        print(f"    - ID: {admin['id']}, Usuario: {admin['usuario']}, Email: {admin['email'] or 'N/A'}")

# Contar usuarios
db.cursor.execute("SELECT COUNT(*) as c FROM usuarios;")
user_count = db.cursor.fetchone()["c"]
print(f"\n  Usuarios clientes: {user_count}")

# 3. Verificar templates
print("\n📄 Verificando templates...")
templates_require = [
    "login_admin.html",
    "admin_setup.html",
    "admin_panel.html",
    "admin_agregar_producto.html"
]

template_dir = "./templates"
for template in templates_require:
    path = os.path.join(template_dir, template)
    if os.path.exists(path):
        print(f"  ✓ {template}")
    else:
        print(f"  ✗ {template} NO EXISTE")

print("\n" + "=" * 60)
print("RESUMEN:")
print("=" * 60)
if admin_count == 0:
    print("⚠️  Necesitas crear un administrador primero.")
    print("   Ve a: http://127.0.0.1:5000/admin/setup")
else:
    print("✓ Sistema configurado. Intenta iniciar sesión en:")
    print("   http://127.0.0.1:5000/admin/login")

print("=" * 60)

db.cerrar()
