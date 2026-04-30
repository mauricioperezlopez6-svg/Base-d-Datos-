import sqlite3

def inicializar_db():
    conexion = sqlite3.connect('tienda.sqlite3')
    cursor = conexion.cursor()
    
    # 1. Creamos la estructura (Requerimiento del Examen)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            imagen TEXT
        )
    ''')
    
    # Limpiamos para no duplicar datos al re-inicializar
    cursor.execute('DELETE FROM productos')

    # 2. Tu catálogo completo de 6 productos para Refill Go
    productos_refill = [
        ('Detergente Multiusos 1L', 'Envase retornable. Fórmula biodegradable ideal para superficies generales y pisos.', 45.00, 100, 'detergente.jpg'),
        ('Suavizante Ecológico 2L', 'Aroma lavanda. Libre de microplásticos y seguro para pieles sensibles.', 70.00, 50, 'suavizante.jpg'),
        ('Jabón Líquido Ropa 3L', 'Fórmula de alto rendimiento para ropa blanca y de color. Protege las fibras.', 110.00, 30, 'jabon_liquido.jpg'),
        ('Lavatrastes Cítrico 1L', 'Corta la grasa al instante. Ingredientes derivados de plantas.', 38.00, 80, 'lavatrastes.jpg'),
        ('Limpiador de Pisos 2L', 'Deja tus pisos brillantes con un fresco aroma a bosque.', 65.00, 40, 'limpiador.jpg'),
        ('Desinfectante Multiusos 1L', 'Elimina el 99.9% de bacterias. Seguro para superficies de cocina y hogar.', 55.00, 60, 'desinfectante.jpg')
    ]
    
    cursor.executemany('INSERT INTO productos (nombre, descripcion, precio, stock, imagen) VALUES (?, ?, ?, ?, ?)', productos_refill)
    conexion.commit()
    conexion.close()
    print("¡Base de datos de Refill Go actualizada con 6 productos!")

if __name__ == '__main__':
    inicializar_db()