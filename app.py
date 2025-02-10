from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_login import LoginManager, login_required, current_user
from auth import auth, login_manager
from database import obtener_conexion
from flask_login import logout_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mi_secreto"  # Necesario para usar flash messages

# Configurar Flask-Login
login_manager.init_app(app)

# Registrar Blueprint de autenticación
app.register_blueprint(auth)

# Ruta principal para mostrar los usuarios registrados
@app.route('/')
@login_required
def index():
    # Conexión a la base de datos
    conexion = obtener_conexion()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios")  # Asumiendo que la tabla es 'usuarios'        
        usuarios = cursor.fetchall()  # Obtener todos los usuarios
        conexion.close()  # Cerrar la conexión
        return render_template('index.html', usuarios=usuarios)
    return "Error al conectar a la base de datos"



# Ruta protegida para agregar usuarios (solo admin)
@app.route('/registro', methods=['GET', 'POST'])
@login_required
def registro():
    if current_user.rol != 'admin':  # Solo admin puede agregar usuarios
        flash("❌ No tienes permiso para agregar equipos", "danger")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        cedula = request.form['cedula']
        username = request.form['username']
        password = request.form['password']
        rol = request.form['rol']
        
     
        # Conexión a la base de datos
        conexion = obtener_conexion()
        if conexion:
            cursor = conexion.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            usuario_existente = cursor.fetchone()
            
            if usuario_existente:
                flash("❌ Error: El usuario ya existe. Intenta con otro.", "danger")
                
            else:
            # Insertar nuevo usuario si el username es único
                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO usuarios (username, password, rol, cedula, nombre, apellido, dinero, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                           (username, hashed_password, rol, cedula, nombre, apellido, 0,"Rechazado"))
                conexion.commit()
                flash("✅ Usuario agregado exitosamente.", "success")
            
            cursor.close()
            conexion.close()
            
            return redirect(url_for('index'))
    return render_template('registro.html')

# Ruta para editar un usuario existente
@app.route('/editar_usuarios/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuarios(id):
    """ Edita un usuario en la base de datos, verificando que el código único no se repita """

    # Conexión a la base de datos
    conexion = obtener_conexion()
    if not conexion:
        flash("❌ Error al obtener la conexión con la base de datos", "danger")
        return redirect(url_for('index'))

    cursor = conexion.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        cedula = request.form['cedula']        
        rol = request.form['rol']

        # Verificar si el usuario ya existe en otro equipo
        cursor.execute("SELECT id FROM usuarios WHERE cedula = %s", (cedula,))
        usuario_existente = cursor.fetchone()

        # Si el código es único, actualiza los datos del equipo
               
        cursor.execute("UPDATE usuarios SET rol=%s, cedula=%s, nombre=%s, apellido=%s WHERE id=%s",
                       (rol, cedula, nombre, apellido, id))
        conexion.commit()
        conexion.close()

        flash("✅ Usuario actualizado correctamente", "success")
        return redirect(url_for('index'))

    # Si es una petición GET, obtener los datos del equipo
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (id,))
    usuario = cursor.fetchone()
    conexion.close()   

    if not usuario:
        flash("❌ El equipo no existe", "danger")
        return redirect(url_for('index'))

    return render_template('editar_usuarios.html', usuario=usuario)

@app.route('/prestamo/<int:id>', methods=['GET', 'POST'])
@login_required
def prestamo(id):
    """ Procesa la solicitud de préstamo, verificando saldo y actualizando el monto. """
    
    conexion = obtener_conexion()
    if not conexion:
        flash("❌ Error al conectar con la base de datos", "danger")
        return redirect(url_for('index'))

    cursor = conexion.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT dinero, estado FROM usuarios WHERE id = %s", (id,))
        usuario = cursor.fetchone()

        if not usuario:
            flash("❌ Usuario no encontrado", "danger")
            return redirect(url_for('index'))

        return render_template("prestamo.html", usuario=usuario, id=id)

    # Obtener datos del formulario
    estado = request.form.get('estado')  # Usamos .get() para evitar KeyError
    dinero = request.form.get('dinero', type=int, default=0)

    # Validar que el estado es correcto
    if not estado or estado not in ["Aprobado", "Rechazado"]:
        flash("⚠️ Debes seleccionar un estado válido.", "warning")
        return redirect(url_for('prestamo', id=id))

    # Obtener saldo actual del administrador (ID=13)
    cursor.execute("SELECT dinero FROM usuarios WHERE id = 13")
    saldo_admin = cursor.fetchone()

    if saldo_admin is None:
        flash("❌ No se encontró el administrador en la base de datos", "danger")
        return redirect(url_for('index'))

    saldo_admin = saldo_admin[0]

    if estado == "Rechazado":
        dinero = 0

    if estado == "Aprobado":
        if dinero <= 0:
            flash("⚠️ El monto no puede ser 0 si el estado del préstamo es aprobado", "warning")
            return redirect(url_for('index'))

        # ⚡ Excepción para ID = 13: No aplicar restricciones de saldo
        if id != 13:
            if saldo_admin == 0:
                flash("⚠️ No hay más dinero disponible para préstamos", "warning")
                return redirect(url_for('index'))

            if dinero > saldo_admin:
                flash(f"⚠️ No hay suficiente dinero en caja. Disponible: ${saldo_admin:,}", "warning")
                return redirect(url_for('index'))

            # Descontar el monto del administrador solo si id != 13
            nuevo_saldo_admin = saldo_admin - dinero
            cursor.execute("UPDATE usuarios SET dinero = %s WHERE id = 13", (nuevo_saldo_admin,))

    # Actualizar estado y dinero del usuario
    cursor.execute("UPDATE usuarios SET estado = %s, dinero = %s WHERE id = %s", (estado, dinero, id))

    conexion.commit()

    # Obtener el nuevo saldo para mostrarlo en la vista actualizada
    cursor.execute("SELECT dinero FROM usuarios WHERE id = 13")
    nuevo_dinero = cursor.fetchone()[0]
    conexion.close()

    flash("✅ Préstamo procesado correctamente", "success")
    
    # Regresamos a la página principal con el nuevo monto actualizado
    return redirect(url_for('index', id_usuario=id, nuevo_dinero=nuevo_dinero))






# Ruta protegida para eliminar (solo admin)
@app.route('/eliminar/<int:id>', methods=['GET'])
@login_required
def eliminar_usuario(id):
    
    if current_user.rol != 'admin':  # Solo admin puede eliminar
        flash("❌ No tienes permiso para eliminar usuarios", "danger")
        return redirect(url_for('index'))
    
    try:
        # Establece la conexión con la base de datos
        conexion = obtener_conexion()
        if conexion:
            with conexion.cursor() as cursor:
                # Ejecuta la consulta SQL para eliminar el equipo por su ID
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
                conexion.commit()
            conexion.close()
            flash("✅ Usuario eliminado correctamente", "success")
            # Redirige a la página principal después de eliminar
            return redirect(url_for('index'))            
        else:
            return "Error al conectar a la base de datos."
    except Exception as e:
        return f"Error al eliminar usuario: {e}"
    
@app.route('/logout')
@login_required
def logout():
    logout_user()  # Cierra la sesión
    flash("✅ Has cerrado sesión", "info")
    return redirect(url_for('auth.login'))

def inject_user():
    return dict(session=session)




if __name__ == '__main__':
    app.run(debug=True)
