from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from database import obtener_conexion

# Se crea un Blueprint llamado 'auth' para manejar las rutas de autenticación
auth = Blueprint('auth', __name__)

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.login_view = "auth.login"  # Especifica la vista de inicio de sesión por defecto

# Clase que representa un usuario autenticado
class Usuario(UserMixin):
    def __init__(self, id, username, password, rol):
        self.id = id  # ID del usuario en la base de datos
        self.username = username  # Nombre de usuario
        self.password = password  # Contraseña encriptada del usuario
        self.rol = rol  # Rol del usuario (ejemplo: admin, usuario)

# Función para cargar un usuario desde la base de datos al autenticarse
@login_manager.user_loader
def load_user(user_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conexion.close()
    
    if user:
        return Usuario(user["id"], user["username"], user["password"], user["rol"])
    return None  # Retorna None si el usuario no existe

# Ruta para el login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
        
        # Verifica si la tabla 'usuarios' existe en la base de datos
        cursor.execute("SHOW TABLES LIKE 'usuarios'")
        table_exists = cursor.fetchone()

        if not table_exists:
            flash("❌ La tabla 'usuarios' no existe en la base de datos.", "danger")
            return render_template('login.html')       

        # Si la tabla existe, procesar el formulario de inicio de sesión
        if request.method == 'POST':
            username = request.form['username']  # Obtiene el usuario ingresado
            password = request.form['password']  # Obtiene la contraseña ingresada

            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            # Verifica que el usuario exista y la contraseña sea correcta
            if user and check_password_hash(user["password"], password):            
                usuario = Usuario(user["id"], user["username"], user["password"], user["rol"]) 
                
                # Guardar datos en la sesión del usuario
                session['usuario_id'] = user['id']
                session['nombre'] = user['nombre']
                session['apellido'] = user['apellido']
                session['dinero'] = user['dinero']
                # flash(f"Dinero del usuario: {session['dinero']}", "info")                
                
                # Obtener el dinero del administrador (id=13)
                cursor.execute("SELECT dinero FROM usuarios WHERE id = %s", (13,))
                admin = cursor.fetchone()
                session['dinero_admin'] = admin['dinero']                 
                
                login_user(usuario)  # Iniciar sesión con Flask-Login
                flash("✅ Inicio de sesión exitoso", "success")
                return redirect(url_for('index'))
            else:
                flash("❌ Usuario o contraseña incorrectos", "danger")            

        return render_template('login.html')
    except Exception as e:
        flash(f"❌ Error al conectar con la base de datos: {str(e)}", "danger")
        return render_template('login.html')

# Ruta para cerrar sesión
@auth.route('/logout')
@login_required  # Requiere que el usuario esté autenticado para acceder
def logout():
    logout_user()
    flash("✅ Has cerrado sesión", "info")
    return redirect(url_for('auth.login'))

# Ruta para verificar la base de datos
@auth.route('/verificar_db')
def verificar_db():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
        
        # Verifica si la tabla 'usuarios' existe
        cursor.execute("SHOW TABLES LIKE 'usuarios'")
        table_exists = cursor.fetchone()

        if not table_exists:
            return "❌ La tabla 'usuarios' no existe en la base de datos."

        # Obtener los usuarios de la tabla
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        conexion.close()

        if usuarios:
            return f"✅ Conexión exitosa. Usuarios encontrados: {len(usuarios)}"
        else:
            return "✅ Conexión exitosa, pero no hay usuarios registrados."
    except Exception as e:
        return f"❌ Error al conectar con la base de datos: {str(e)}"
    
# Ruta para registrar un nuevo usuario
@auth.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        cedula = request.form['cedula']
        username = request.form['username']
        password = request.form['password']
        
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            
            # Verifica si el usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE username = %s and cedula = %s", (username, cedula,))
            usuario_existente = cursor.fetchone()
            
            if usuario_existente:
                flash("❌ Error: El usuario ya existe. Intenta con otro.", "danger")
            else:
                # Inserta un nuevo usuario con la contraseña encriptada
                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO usuarios (username, password, rol, cedula, nombre, apellido, dinero, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                               (username, hashed_password, "usuario", cedula, nombre, apellido, 0, "Rechazado"))
                conexion.commit()
                flash("✅ Usuario agregado exitosamente.", "success")
            
            cursor.close()
            conexion.close()
            
            return redirect(url_for('auth.login'))
    return render_template('registrar.html')
