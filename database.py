import pymysql

# Función para obtener la conexión a la base de datos MySQL
def obtener_conexion():
    try:
        # Realiza la conexión con la base de datos MySQL
        conexion = pymysql.connect(
            host='localhost',      # El host donde está tu base de datos
            user='root',           # El usuario con el que te conectas (puede ser 'root' u otro)
            password='admin',# La contraseña del usuario (cambia 'tu_password' por la correcta)
            database='fpc'   # El nombre de la base de datos a la que te conectas
        )
        return conexion
    except Exception as e:
        print(f"❌ Error al conectar a MySQL: {e}")
        return None

# Función para verificar la conexión
def verificar_conexion():
    conexion = obtener_conexion()
    if conexion:
        print("✅ Conexión exitosa a la base de datos MySQL.")
        conexion.close()  # Cierra la conexión una vez verificada
    else:
        print("❌ No se pudo conectar a la base de datos.")

# Si ejecutas este archivo directamente, verificamos la conexión
if __name__ == "__main__":
    verificar_conexion()
