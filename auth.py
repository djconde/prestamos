from flask import Blueprint, render_template, request, redirect, url_for,session, flash 
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from database import obtener_conexion

auth = Blueprint('auth', __name__)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.login_view = "auth.login"

# Modelo de usuario
class Usuario(UserMixin):
    def __init__(self, id, username, password, rol):
        self.id = id
        self.username = username
        self.password = password
        self.rol = rol

# Cargar usuario
@login_manager.user_loader
def load_user(user_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conexion.close()
    
    if user:
        return Usuario(user["id"], user["username"], user["password"], user["rol"])
    return None

@auth.route('/login', methods=['GET', 'POST'])
def login():
    try:
        # Probar la conexión a la base de datos
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
        
        # Verificar si la tabla 'usuarios' existe
        cursor.execute("SHOW TABLES LIKE 'usuarios'")
        table_exists = cursor.fetchone()

        if not table_exists:
            flash("❌ La tabla 'usuarios' no existe en la base de datos.", "danger")
            return render_template('login.html')       

        # Si la tabla existe y la conexión es correcta, continuar con el login
        if request.method == 'POST':
            username = request.form['username']          
            password = request.form['password']             

            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user = cursor.fetchone()            
            conexion.close()          
            
            #if user and user["password"] == password:  # Comparación directa sin hashing
            if user and check_password_hash(user["password"], password):            
                usuario = Usuario(user["id"], user["username"], user["password"], user["rol"]) 
                               
                session['usuario_id'] = user['id']
                session['nombre'] = user['nombre']
                session['apellido'] = user['apellido']
                session['dinero'] = user['dinero']
                
                login_user(usuario)                
                flash("✅ Inicio de sesión exitoso", "success")
                return redirect(url_for('index'))
        
            else:
                flash("❌ Usuario o contraseña incorrectos", "danger")           

        return render_template('login.html')

    except Exception as e:
        flash(f"❌ Error al conectar con la base de datos: {str(e)}", "danger")
        return render_template('login.html')

# Ruta de logout
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("✅ Has cerrado sesión", "info")
    return redirect(url_for('auth.login'))

@auth.route('/verificar_db')
def verificar_db():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor=pymysql.cursors.DictCursor)
        
        # Verificar si la tabla 'usuarios' existe
        cursor.execute("SHOW TABLES LIKE 'usuarios'")
        table_exists = cursor.fetchone()

        if not table_exists:
            return "❌ La tabla 'usuarios' no existe en la base de datos."

        # Intentar obtener los usuarios de la tabla
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        conexion.close()

        if usuarios:
            return f"✅ Conexión exitosa. Usuarios encontrados: {len(usuarios)}"
        else:
            return "✅ Conexión exitosa, pero no hay usuarios registrados."

    except Exception as e:
        return f"❌ Error al conectar con la base de datos: {str(e)}"
    
@auth.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        cedula = request.form['cedula']
        username = request.form['username']
        password = request.form['password']
             
        # Conexión a la base de datos
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE username = %s and cedula = %s", (username, cedula,))
            usuario_existente = cursor.fetchone()
            
            if usuario_existente:
                flash("❌ Error: El usuario ya existe. Intenta con otro.", "danger")
                
            else:
            # Insertar nuevo usuario si el username es único
                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO usuarios (username, password, rol, cedula, nombre, apellido, dinero, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                           (username, hashed_password, "usuario", cedula, nombre, apellido, 0,"Rechazado"))
                conexion.commit()
                flash("✅ Usuario agregado exitosamente.", "success")
            
            cursor.close()
            conexion.close()
            
            return redirect(url_for('auth.login'))
    return render_template('registrar.html')


    
    
 

