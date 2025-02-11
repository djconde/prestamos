from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_login import LoginManager, login_required, current_user
from auth import auth, login_manager
from database import obtener_conexion
from flask_login import logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging


app = Flask(__name__)
app.secret_key = "mi_secreto"  # Necesario para usar flash messages

# Configurar Flask-Login
login_manager.init_app(app)

# Registrar Blueprint de autenticación
app.register_blueprint(auth)

@app.route('/')
@login_required
def index():
    # Conexión a la base de datos
    conexion = obtener_conexion()   
    if not conexion:
        flash("❌ Error al conectar con la base de datos", "danger")
        return "Error al conectar a la base de datos"
    
    cursor = conexion.cursor()

    # Obtener el ID del usuario autenticado
    id_usuario = current_user.id

    # Obtener los datos actualizados del usuario desde la base de datos
    cursor.execute("SELECT dinero FROM usuarios WHERE id = %s", (id_usuario,))
    usuario_data = cursor.fetchone()
    
    if not usuario_data:
        flash("❌ No se encontraron datos del usuario", "danger")
        return redirect(url_for('logout'))  # Redirigir a logout si no existe en la BD

    # Actualizar sesión con el dinero actual del usuario
    dinero_admin = usuario_data[0]
    session['dinero_admin'] = dinero_admin  # Almacena el dinero actualizado

    # Obtener todos los usuarios para mostrarlos en el index
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()

    conexion.close()  # Cerrar la conexión

    return render_template('index.html', 
                           usuarios=usuarios, 
                           id_usuario=id_usuario, 
                           dinero_admin=dinero_admin)
    
@app.route('/usuarios')
@login_required
def usuarios():
    # Conexión a la base de datos
    conexion = obtener_conexion()   
    if not conexion:
        flash("❌ Error al conectar con la base de datos", "danger")
        return "Error al conectar a la base de datos"
    
    cursor = conexion.cursor()

    # Obtener el ID del usuario autenticado
    id_usuario = current_user.id   

    # Obtener todos los usuarios para mostrarlos en el index
    cursor.execute("SELECT cedula FROM usuarios WHERE id = %s", (id_usuario,))
    usuario = cursor.fetchone()

    conexion.close()  # Cerrar la conexión

    return render_template('usuarios.html', 
                           usuario=usuario, 
                           id_usuario=id_usuario, 
                           )


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
        if current_user.rol != 'admin':  # Solo admin puede eliminar        
            return redirect(url_for('usuarios'))
        else:
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
        
        if current_user.rol != 'admin':
            # Si el código es único, actualiza los datos del equipo               
            cursor.execute("UPDATE usuarios SET rol=%s, cedula=%s, nombre=%s, apellido=%s WHERE id=%s",
                       ("usuario", cedula, nombre, apellido, id))
            flash("✅ Usuario administrador ha actualizado correctamente", "success")
            conexion.commit()
            conexion.close()  
            return redirect(url_for('usuarios'))
        else:
            # Si el código es único, actualiza los datos del equipo               
            cursor.execute("UPDATE usuarios SET rol=%s, cedula=%s, nombre=%s, apellido=%s WHERE id=%s",
                       (rol, cedula, nombre, apellido, id))
            flash("✅ se ha actualizado correctamente tus datos", "success")
            conexion.commit()
            conexion.close()  
            return redirect(url_for('index'))       

    # Si es una petición GET, obtener los datos del equipo
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (id,))
    usuario = cursor.fetchone()
    conexion.close()   

    if not usuario:
        flash("❌ El equipo no existe", "danger")
        return redirect(url_for('index'))

    if current_user.rol != 'admin':
        return render_template('editar_usuario.html', usuario=usuario)
    else:
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
    
    if current_user.rol != 'admin':  # Solo admin puede hacer prestamos
        flash("❌ Solo el usuario administrador puede hacer prestamos", "danger")
        return redirect(url_for('index'))
    
    if request.method == 'GET':
        # Obtener los datos del usuario con id = 13 (administrador)
        cursor.execute("SELECT dinero FROM usuarios WHERE id = 13")
        saldo_admin = cursor.fetchone()
        
        if not saldo_admin:
            flash("❌ No se encontró el administrador en la base de datos", "danger")
            return redirect(url_for('index'))

        saldo_admin = saldo_admin[0]  # El saldo del administrador (usuario con id = 13) 
        # Obtener los datos del usuario seleccionado
        cursor.execute("SELECT id, nombre, apellido, dinero, estado,cedula, username, password FROM usuarios WHERE id = %s", (id,))
        usuario = cursor.fetchone()       

        if not usuario:
            flash("❌ Usuario no encontrado", "danger")
            return redirect(url_for('index'))
        
        if usuario[4]=="Aprobado":
            flash("❌ El usuario ya tiene un Prestamo aprobado, este no se puede modificar", "danger")
            return redirect(url_for('index'))        
        

        # Pasar todos los datos a la plantilla
        return render_template("prestamo.html", usuario=usuario, id=id, saldo_admin=saldo_admin)

    # Aquí sigue el procesamiento del formulario POST...
    estado = request.form.get('estado')
    dinero = request.form.get('dinero', type=int, default=0)
    nuevo_dinero = request.form.get('nuevo_dinero')  # Obtener el nuevo dinero enviado desde el formulario    

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
        if dinero > 0:
            estado = "Aprobado"
            flash("⚠️ Ya cuenta con un prestamo activo no se puede otorgar mas prestamos", "warning")            

    if estado == "Aprobado":
        if dinero <= 0:
            flash("⚠️ El monto no puede ser 0 si el estado del préstamo es aprobado", "warning")
            return redirect(url_for('prestamo', id=id))

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

    # Si el nuevo dinero enviado desde el formulario es diferente al dinero actual en la sesión, actualizar la sesión
    if nuevo_dinero:
        if nuevo_dinero != session.get('dinero_admin', None):
            session['dinero_admin'] = nuevo_dinero  # Actualiza el valor en la sesión
            logging.warning(f"Nuevo dinero guardado en sesión: {nuevo_dinero}")
    
    # Obtener el nuevo saldo para mostrarlo en la vista actualizada
    cursor.execute("SELECT dinero FROM usuarios WHERE id = 13")
    nuevo_dinero = cursor.fetchone()[0]
    conexion.close()

    flash("✅ Préstamo procesado correctamente", "success")
    
    # Redirige a la página de index con el id_usuario y nuevo_dinero
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
    
    
@app.route('/cambiar_contrasena/<int:id>', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena(id):
    conexion = obtener_conexion()
    if not conexion:
        flash("❌ Error al conectar con la base de datos", "danger")
        return redirect(url_for('index'))

    cursor = conexion.cursor()
    cursor.execute("SELECT nombre, apellido, cedula, username, password,id FROM usuarios WHERE id = %s", (id,))
    usuario = cursor.fetchone()    

    if not usuario:
        flash("❌ Usuario no encontrado", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        contrasena_actual = request.form['contrasena_actual']
        nueva_contrasena = request.form['nueva_contrasena']
        confirmar_contrasena = request.form['confirmar_contrasena']

        # Verificar la contraseña actual
        if not check_password_hash(usuario[4], contrasena_actual):
            flash("❌ La contraseña actual es incorrecta", "danger")
            return redirect(url_for('cambiar_contrasena', id=id))

        # Validaciones de la nueva contraseña
        if len(nueva_contrasena) < 5 or not any(c.isdigit() for c in nueva_contrasena) or not any(c.isalpha() for c in nueva_contrasena):
            flash("⚠️ La nueva contraseña debe tener al menos 5 caracteres, incluir números y letras.", "warning")
            return redirect(url_for('cambiar_contrasena', id=id))

        if nueva_contrasena != confirmar_contrasena:
            flash("⚠️ Las contraseñas no coinciden.", "warning")
            return redirect(url_for('cambiar_contrasena', id=id))

        # Actualizar la contraseña en la base de datos
        nueva_contrasena_hashed = generate_password_hash(nueva_contrasena)
        cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (nueva_contrasena_hashed, id))
        conexion.commit()
        conexion.close()

        flash("✅ Contraseña actualizada exitosamente", "success")
        return redirect(url_for('index'))

    return render_template('cambiar_contrasena.html', usuario=usuario)

# Rutas de la aplicación principal
@app.route('/inicio')
def inicio():
    return render_template('index.html')
    
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
