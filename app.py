"""
Este archivo contiene la implementación de una aplicación web utilizando Flask y SQLAlchemy.
La aplicación gestiona la autenticación de usuarios, permite a los usuarios agregar
y gestionar repositorios de GitHub, y proporciona información detallada sobre los repositorios.

Autores:
 - Víctor González Del Campo
 - Alberto Santos Martínez
 - Mario Sanz Pérez
"""
from datetime import datetime
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, flash, redirect, render_template, url_for
from flask import request, session as flask_session
from flask_session import Session
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.orm import Session, DeclarativeBase, Mapped
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy import select, create_engine, desc
from sqlalchemy import func
from dotenv import load_dotenv
import os


class Base(DeclarativeBase):
    """
    Clase base para la definición de modelos de la base de datos.
    """


class User(Base):
    """
    Clase que representa una cuenta de usuario.

    Atributos:
    - id: Identificador único de la cuenta de usuario.
    - username: Nombre de usuario de la cuenta.
    - password: Contraseña de la cuenta.
    """
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password: Mapped[str]

class Repositorios(Base):
    """
    Clase que representa una tabla de repositorios en la base de datos.

    Atributos:
    - id: Identificador único del repositorio (clave primaria)
    - owner: Propietario del repositorio
    - repo: Nombre del repositorio
    - fecha_ultima_actualizacion: Fecha de la última actualización del repositorio
    - num_forks: Número de forks del repositorio (valor predeterminado: 0, puede ser nulo)
    - num_stars: Número de estrellas del repositorio (valor predeterminado: 0, puede ser nulo)
    - default_branch: Rama predeterminada del repositorio
    - num_open_issues: Número de issues abiertos del repositorio (valor predeterminado: 0)
    - fecha_creacion: Fecha de creación del repositorio
    """
    __tablename__ = "repositorios"
    id = Column(Integer, primary_key=True)
    owner = Column(String(30))
    repo = Column(String(30))
    fecha_ultima_actualizacion = Column(Date)
    num_forks = Column(Integer, default=0, nullable=True)
    num_stars = Column(Integer, default=0, nullable=True)
    default_branch = Column(String(50))
    num_open_issues = Column(Integer, default=0)
    fecha_creacion = Column(Date)


class UserRepo(Base):
    """
    Clase que representa la relación entre un usuario y un repositorio.

    Atributos:
    - user_id (int): ID del usuario.
    - repo_id (int): ID del repositorio.
    - favorito (bool): Indica si el repositorio es favorito del usuario.

    Relaciones:
    - user (User): Relación con la tabla User.
    - repo (Repositorios): Relación con la tabla Repositorios.
    """
    __tablename__ = "user_repo"
    user_id = Column(Integer, ForeignKey("user_account.id"), primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositorios.id"), primary_key=True)
    favorito = Column(Boolean, default=False)

    user = relationship("User", backref="user_repos")
    repo = relationship("Repositorios", backref="repo_users")



load_dotenv('.')  # Carga las variables de entorno del archivo .env
# Crea la base de datos en la carpeta BD
database_name = os.getenv("DATABASE_NAME")
database_url = f"sqlite:///./BD/{database_name}.sqlite"
engine = create_engine(database_url, echo=True)
Base.metadata.create_all(engine)

github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    raise Exception("No se ha encontrado el token de GitHub en el archivo .env")
headers = {"Authorization": f"Bearer {github_token}"}


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route("/")
def home():
    """
    Función que maneja la ruta principal del sitio web.

    Returns:
        - La plantilla 'bienvenido.html'.
    """
    return render_template('bienvenido.html')



@app.get("/register")
def register_get():
    """
    Función que maneja la solicitud GET en la ruta '/register'.
    Renderiza la plantilla 'register.html'.

    Returns:
        - El contenido de la plantilla 'register.html'.
    """
    return render_template('register.html')

def validate_credentials (username, password):
    """
    Función que valida las credenciales de un usuario.

    Parámetros:
    - username (str): Nombre de usuario.
    - password (str): Contraseña.

    Returns:
        - True si las credenciales son válidas.
        - False si las credenciales no son válidas.
    """
    return len(username) > 0 and len(password) >= 6

def register_user(username, password):
    """
    Función que registra un nuevo usuario en la base de datos.

    Parámetros:
    - username (str): Nombre de usuario.
    - password (str): Contraseña.

    Returns:
        - El usuario recién creado.
    """
    hashed_password = generate_password_hash(password)

    with Session(engine) as session:
        try:
            user = User(
                username=username,
                password=hashed_password
            )

            session.add(user)
            session.commit()
            return user.id
        except IntegrityError:
            session.rollback()
            raise ValueError('Error: El nombre de usuario ya está en uso. Por favor, elige otro.')

def set_session_cookie(user_id):
    """
    Función que establece la cookie de sesión con el ID del usuario.

    Parámetros:
    - user_id (int): ID del usuario.
    """
    flask_session['user_id'] = user_id
    
    
@app.post("/register")
def register_post():
    """
    Procesa la solicitud POST para el registro de un nuevo usuario.

    Esta función obtiene el nombre de usuario y la contraseña del formulario de la solicitud.
    Realiza validaciones adicionales, como verificar la longitud de la contraseña.
    Si los datos son válidos, crea un nuevo usuario en la base de datos
    y establece la cookie de sesión con el ID del usuario.
    Si el nombre de usuario ya está en uso, muestra un mensaje de error.

    Returns:
        - Si el registro es exitoso, redirige al usuario a la página principal.
        - Si hay errores en los datos de registro, muestra un mensaje de error
            y renderiza la plantilla de registro nuevamente.
    """
    username = request.form['username']
    password = request.form['password']

    if not validate_credentials(username, password):
        flash('Usuario o contraseña no válidos')
        return render_template('register.html')

    try:
        usuario_id = register_user(username, password)
        set_session_cookie(usuario_id)
        flash('Te has registrado satisfactoriamente')
        return redirect(url_for('principal'))
    except ValueError as e:
        flash(str(e))
    
    return render_template('register.html')



@app.get('/login/')
def login_get():
    """
    Renderiza la plantilla 'login.html' para la página de inicio de sesión.

    Returns:
        - Una instancia de la plantilla 'login.html'
    """
    return render_template('login.html')

def login_user(username, password):
    """
    Función que inicia sesión con las credenciales de un usuario.

    Parámetros:
    - username (str): Nombre de usuario.
    - password (str): Contraseña.

    Returns:
        - El usuario que ha iniciado sesión.
    """
    with Session(engine) as session:
        usuario = session.scalar(
            select(User).where(User.username == username)
        )
        if usuario and check_password_hash(usuario.password, password):
            set_session_cookie(usuario.id)
            return usuario
        else:
            raise ValueError('Nombre de usuario o contraseña incorrectos')

@app.post('/login/')
def login_post():
    """
    Procesa la solicitud POST para el inicio de sesión.

    Esta función recibe los datos de inicio de sesión del usuario, 
    verifica si las credenciales son válidas y realiza las acciones 
    correspondientes en caso de éxito o fracaso del inicio de sesión.

    Returns:
    - Si las credenciales son válidas, establece la cookie de sesión con el ID del usuario y
      redirige a la página principal.
    - Si las credenciales son inválidas, muestra un mensaje de error
      y redirige a la página de inicio de sesión.

    """
    error = None
    username = request.form['username']
    password = request.form['password']

    try:
        user = login_user(username, password)
        flash('¡Te has logueado satisfactoriamente!', 'success')
        return redirect(url_for('principal'))
    except ValueError as e:
        flash('Inicio de sesión fallido. ' + str(e), 'error')

    return render_template(
        'login.html',
        username = username
    )



@app.errorhandler(404)
def page_not_found(error):
    """
    Manejador de errores para la página no encontrada (404).
    Renderiza la plantilla 'pagina_no_encontrada.html' y devuelve el código de estado 404.

    Returns:
        - Una instancia de la plantilla 'pagina_no_encontrada.html' con el código de estado 404.
    """
    return render_template('pagina_no_encontrada.html'), error.code



@app.route('/principal')
def principal():
    """
    Vista para la página principal del usuario.

    Obtiene el ID del usuario de la sesión y todos los UserRepo del usuario actual.
    Crea un diccionario para mapear el ID del repositorio con su estado de favorito.
    Obtiene todos los repositorios que el usuario ha agregado.
    Obtiene los tres repositorios más comunes.
    Obtiene los detalles de los tres repositorios más comunes.
    Obtiene el nombre de usuario.
    Envía los datos de los repositorios, los favoritos,
    los detalles de los repositorios y el nombre de usuario a la plantilla HTML.

    Returns:
        - La plantilla HTML 'principal.html' con los datos de los repositorios, los favoritos,
         los detalles de los repositorios y el nombre de usuario.
    """
    if 'user_id' not in flask_session:
        # Redirige al login si el usuario no está en sesión
        return redirect(url_for('login_get'))

    user_id = flask_session['user_id']  # Obtener el ID del usuario de la sesión

    with Session(engine) as session:
        # Obtener todos los UserRepo del usuario actual
        user_repos = session.query(UserRepo).filter(
            UserRepo.user_id == user_id
            ).all()

        # Crear un diccionario para mapear repo_id a estado de favorito
        favoritos = {ur.repo_id: ur.favorito for ur in user_repos}

        # Obtener todos los repositorios que el usuario ha agregado
        repositorios = session.query(Repositorios).join(
            UserRepo, Repositorios.id == UserRepo.repo_id
            ).filter(
                UserRepo.user_id == user_id
                ).all()

        # Obtener los tres repositorios más comunes
        top_repos = session.query(
            UserRepo.repo_id,
            func.count(UserRepo.user_id
                       ).label('user_count')).group_by(
                           UserRepo.repo_id
                           ).order_by(
                               desc('user_count')
                               ).limit(3).all()

        top_repo_details = session.query(Repositorios).filter(
            Repositorios.id.in_([repo_id for repo_id, _ in top_repos])
            ).all()

        # Obtener el nombre de usuario
        user = session.query(User).filter(
            User.id == user_id
            ).first()
        username = user.username if user else None

        # Enviar los datos de los repositorios y los favoritos a la plantilla HTML
        return render_template(
            'principal.html', 
            repositorios = repositorios,
            favoritos = favoritos,
            top_repo_details = top_repo_details,
            top_repos = top_repos,
            username = username)



@app.get('/principal/add')
def add_get():
    """
    Renderiza la plantilla 'add.html' si el usuario ha iniciado sesión.
    Si el usuario no ha iniciado sesión,
    muestra un mensaje y redirige a la página de inicio de sesión.

    Returns:
        - Una instancia de la plantilla 'add.html'
    """
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para agregar elementos.")
        return redirect(url_for('login_get'))

    return render_template('add.html')



@app.post('/principal/add')
def add_post():
    """
    Maneja la solicitud POST para agregar un repositorio a la base de datos.

    Obtiene el nombre del repositorio ingresado por el usuario y verifica si existe utilizando
    la API de GitHub. Si el repositorio existe, se extraen los datos relevantes, como la fecha 
    de última actualización, el número de estrellas, el número de forks, etc.
    A continuación, se verifica si el repositorio ya existe en la base de datos. 
    Si es así, se actualizan los datos existentes.
    Si el repositorio no existe, se crea un nuevo registro en la base de datos.
    Si no es así, se agrega a la tabla user_repo.
    Finalmente, se redirige a la página de detalles del repositorio recién agregado/actualizado.

    Returns:
        - redirect: Redirige a la página de detalles del repositorio.
    """
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para agregar repositorios.")
        return redirect(url_for('login_get'))

    repo_input = request.form['repositorio']
    try:
        owner, repo_name = repo_input.split('/')
    except ValueError:
        flash("Formato de repositorio incorrecto. Usa el formato 'owner/repo'.")
        return redirect(url_for('add_get'))

    # Utiliza la API de GitHub para verificar si el repositorio existe
    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    response = requests.get(url, timeout=5, headers=headers)
    if response.status_code != 200:
        flash("El repositorio no existe en GitHub o no tiene autorizacion.")
        return redirect(url_for('add_get'))

    repo_data = response.json()

    repo_info = {
        # Convertir las fechas a objetos de fecha
        'fecha_ultima_actualizacion': datetime.strptime(
                                    repo_data['updated_at'],
                                    '%Y-%m-%dT%H:%M:%SZ'
                                    ).date(),
        'num_stars': repo_data['stargazers_count'],
        'num_forks': repo_data['forks_count'],
        'default_branch': repo_data['default_branch'],
        'num_open_issues': repo_data['open_issues_count'],
        'fecha_creacion': datetime.strptime(
                        repo_data['created_at'],
                        '%Y-%m-%dT%H:%M:%SZ'
                        ).date()
    }

    with Session(engine) as session:
        try:
            # Verificar si el repositorio ya existe en la base de datos
            repositorio = session.query(Repositorios).filter_by(
                owner = owner,
                repo = repo_name
                ).first()
            if repositorio:
                # Actualizar los datos existentes
                for key, value in repo_info.items():
                    setattr(repositorio, key, value)
            else:
                # Crear un nuevo registro si el repositorio no existe en la base de datos
                nuevo_repositorio = Repositorios(
                    owner = owner,
                    repo = repo_name,
                    **repo_info
                )
                session.add(nuevo_repositorio)
                session.flush()  # Obtener el ID del nuevo repositorio
                repositorio = nuevo_repositorio

            # Insertar una fila en la tabla user_repo
            user_id = flask_session['user_id']  # Obtener el ID del usuario actual
            user_repo = session.query(UserRepo).filter_by(
                user_id = user_id,
                repo_id = repositorio.id
                ).first()
            if not user_repo:
                # Si el usuario no tiene este repositorio, añadirlo
                user_repo = UserRepo(
                    user_id = user_id,
                    repo_id = repositorio.id)
                session.add(user_repo)

            session.commit()
            flash("Repositorio añadido/actualizado exitosamente.")
        except SQLAlchemyError:
            session.rollback()
            flash("Error al añadir/actualizar el repositorio en la base de datos.")

    return redirect(
        url_for(
            'detalles_get',
            owner = owner,
            repo = repo_name)
        )



@app.get('/principal/detalles/<owner>/<repo>')
def detalles_get(owner, repo):
    """
    Obtiene los detalles de un repositorio específico.

    Parámetros:
    - owner (str): Nombre del propietario del repositorio.
    - repo (str): Nombre del repositorio.

    Returns:
    - Si el usuario no ha iniciado sesión, redirige a la página de inicio de sesión.
    - Si el repositorio no existe, redirige a la página principal.
    - Si el usuario no tiene acceso al repositorio, redirige a la página principal.
    - Si todo es correcto, renderiza la plantilla 'detalles.html' con los detalles del repositorio
      y la relación del usuario con el repositorio.
    """
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para ver los detalles del repositorio.")
        return redirect(url_for('login_get'))

    with Session(engine) as session:
        # Verificar si el repositorio pertenece al usuario en sesión
        repositorio = session.query(Repositorios).filter_by(
            owner = owner,
            repo = repo
            ).first()
        if not repositorio:
            flash("Repositorio no encontrado.")
            return redirect(url_for('principal'))

        user_repo = session.query(UserRepo).filter_by(
            user_id = flask_session['user_id'],
            repo_id = repositorio.id
            ).first()
        if not user_repo:
            flash("No tienes este repositorio en tu lista.")
            return redirect(url_for('principal'))

        return render_template(
            'detalles.html',
            repositorio = repositorio,
            user_repo = user_repo
            )



@app.post('/principal/detalles/<owner>/<repo>')
def detalles_post(owner, repo):
    """
    Muestra los detalles de un repositorio en la base de datos
    y permite al usuario actualizar los detalles.

    Parámetros:
    - owner (str): Nombre del propietario del repositorio.
    - repo (str): Nombre del repositorio.

    Returns:
    - Redirecciona a la página principal cuando se le da a "Volver a la Página Principal".
    - Redirecciona a la página de detalles del repositorio actualizado cuando
      se le da a actualizar.

    Comentarios:
    - Comprueba si el usuario ha iniciado sesión. Si no ha iniciado sesión,
      redirige a la página de inicio de sesión.
    - Realiza una solicitud a la API de GitHub para obtener los datos del repositorio.
    - Comprueba si el repositorio existe en la base de datos. Si no existe,
      muestra un mensaje de error y redirige a la página principal.
    - Comprueba si el usuario tiene el repositorio en su lista. Si no lo tiene,
      muestra un mensaje de error y redirige a la página principal.
    - Si la solicitud a la API de GitHub es exitosa,
      actualiza los detalles del repositorio en la base de datos.
    - Si ocurre un error al actualizar la base de datos, muestra un mensaje de error.
    - Redirige a la página de detalles del repositorio actualizado.
    """
    if 'user_id' not in flask_session:
        return redirect(url_for('login_get'))

    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, timeout=5, headers=headers)

    with Session(engine) as session:
        repositorio = session.query(Repositorios).filter_by(
            owner = owner,
            repo = repo
            ).first()
        if not repositorio:
            flash("Repositorio no encontrado en la base de datos.")
            return redirect(url_for('principal'))

        user_repo = session.query(UserRepo).filter_by(
            user_id = flask_session['user_id'],
            repo_id = repositorio.id
            ).first()
        if not user_repo:
            flash("No tienes este repositorio en tu lista.")
            return redirect(url_for('principal'))

        if response.status_code != 200:
            flash(f"El repositorio {owner}/{repo} ya no está disponible en GitHub.")
            return redirect(
                url_for(
                    'detalles_get',
                    owner = owner,
                    repo = repo)
                )

        repo_data = response.json()

        fecha_ultima_actualizacion = datetime.strptime(
            repo_data['updated_at'],
            '%Y-%m-%dT%H:%M:%SZ'
            ).date()
        fecha_creacion = datetime.strptime(
            repo_data['created_at'],
            '%Y-%m-%dT%H:%M:%SZ'
            ).date()
        num_stars = repo_data['stargazers_count']
        num_forks = repo_data['forks_count']
        default_branch = repo_data['default_branch']
        num_open_issues = repo_data['open_issues_count']

        repositorio.fecha_ultima_actualizacion = fecha_ultima_actualizacion
        repositorio.fecha_creacion = fecha_creacion
        repositorio.num_stars = num_stars
        repositorio.num_forks = num_forks
        repositorio.default_branch = default_branch
        repositorio.num_open_issues = num_open_issues

        try:
            session.commit()
            flash("Repositorio actualizado exitosamente.")
        except SQLAlchemyError:
            session.rollback()
            flash("Error al actualizar el repositorio en la base de datos.")

        return redirect(
            url_for(
                'detalles_get',
                owner = owner,
                repo = repo)
            )



@app.post('/alternar_favorito/<int:repo_id>')
def alternar_favorito(repo_id):
    """
    Alternar el estado de favorito de un repositorio para un usuario específico.

    Parámetros:
    - repo_id (int): El ID del repositorio que se desea marcar como favorito.

    Returns:
    - redirect: Redirige al referer o a la página principal después de actualizar
      el estado de favorito.

    Comentarios:
    - Si el usuario no ha iniciado sesión, se muestra un mensaje de error
      y se redirige a la página de inicio de sesión.
    - Si el repositorio no existe para el usuario, se muestra un mensaje de error
      y se redirige a la página principal.
    - El estado de favorito del repositorio se alterna (se cambia de True a False o viceversa).
    - Se realiza una transacción en la base de datos para actualizar el estado de favorito.
    - Se muestra un mensaje de éxito o error dependiendo del resultado de la transacción.
    """
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para marcar repositorios como favoritos.")
        return redirect(url_for('login_get'))

    with Session(engine) as session:
        user_repo = session.query(UserRepo).filter_by(
            user_id = flask_session['user_id'],
            repo_id = repo_id
            ).first()
        if user_repo is None:
            flash('El repositorio no existe')
            return redirect(request.referrer or url_for('principal'))

        # Alternar el estado de favorito
        user_repo.favorito = not user_repo.favorito

        try:
            session.commit()
            flash("Estado de favorito actualizado exitosamente.")
        except SQLAlchemyError:
            session.rollback()
            flash("Error al actualizar el estado de favorito en la base de datos.")

    # Redirigir al referer, o a la página principal si no hay referer
    return redirect(request.referrer or url_for('principal'))


@app.route("/logout")
def logout():
    """
    Elimina al usuario de la sesión y lo redirecciona a la página home.
    
    Returns:
        - Devuelve al usuario a la página home.
    """
    flask_session.pop('user_id', None)
    return redirect(url_for('home'))
