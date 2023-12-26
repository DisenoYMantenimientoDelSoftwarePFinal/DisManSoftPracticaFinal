import requests
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, flash, redirect, render_template, request, session as flask_session, url_for
from sqlalchemy import Column, Integer, String, Boolean, Date
from datetime import datetime
from flask_session import Session


from markupsafe import escape

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy.orm import mapped_column
from typing import List, Optional
from sqlalchemy import select, Date, Column
from sqlalchemy import create_engine
from datetime import date


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password: Mapped[str] # Hemos quitado Optional porque no queremos que sea nulo

class Repositorios(Base):
    __tablename__ = "repositorios"
    id = Column(Integer, primary_key=True)
    owner = Column(String(30))
    repo = Column(String(30))
    fecha_ultima_actualizacion = Column(Date)
    favorito = Column(Boolean, default=False)
    num_forks = Column(Integer, default=0, nullable=True)
    num_stars = Column(Integer, default=0, nullable=True)
    default_branch = Column(String(50))
    num_open_issues = Column(Integer, default=0)
    fecha_creacion = Column(Date)


class UserRepo(Base):
    __tablename__ = "user_repo"
    user_id = Column(Integer, ForeignKey("user_account.id"), primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositorios.id"), primary_key=True)

    # Definir relaciones con las tablas User y Repositorios
    user = relationship("User", backref="user_repos")
    repo = relationship("Repositorios", backref="repo_users")

engine = create_engine("sqlite:///./BD/githubExplorer.sqlite", echo=True)
Base.metadata.create_all(engine)

from sqlalchemy.orm import Session




app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Configura flask_session para usar cookies de sesión
app.config['SESSION_TYPE'] = 'filesystem'  # Puedes cambiar el tipo según tus necesidades
Session(app)

@app.route("/")
def home():
    return render_template('bienvenido.html')


@app.get("/register")   
def register_get():
    return render_template('register.html')

@app.post("/register")
def register_post():
    username = request.form['username']
    password = request.form['password']

    # Validaciones adicionales, si es necesario (p. ej., longitud de contraseña)
    if len(username) == 0 or len(password) < 6:
        flash('Usuario o contraseña no válidos')
        return render_template('register.html')

    hashed_password = generate_password_hash(password)

    with Session(engine) as session:
        try:
            usuario = User(username=username, password=hashed_password)

            session.add(usuario)
            session.commit()
            flask_session['user_id'] = usuario.id  # Establecer la cookie de sesión con el ID del usuario
            flash('Te has registrado satisfactoriamente')
            return redirect(url_for('principal'))
        except IntegrityError as e:
            session.rollback()
            flash('Error al registrar: El nombre de usuario ya está en uso. Por favor, elige otro.')

    return render_template('register.html')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'    

@app.get('/login/')
def login_get():
   return render_template('login.html')

@app.post('/login/')
def login_post():
    error = None
    username = request.form['username']
    password = request.form['password']

    with Session(engine) as session:
        usuario = session.scalar(
            select(User).where(User.username == username)
        )
        if usuario and check_password_hash(usuario.password, password):
            flask_session['user_id'] = usuario.id  # Establecer la cookie de sesión con el ID del usuario
            flash('¡Te has logueado satisfactoriamente!', 'success')
            return redirect(url_for('principal'))
        else:
            error = 'Nombre de usuario o contraseña incorrectos'
            flash('Inicio de sesión fallido. ' + error, 'error')

    return render_template(
        'login.html',
        error=error,
        username=username
    )

#stmt = select(User).where(User.name.in_(["spongebob", "sandy"]))



def authenticate(username, password):
    #TODO: Autenticar a un usuario con una base de datos
    return ADMIN_USERNAME == username and ADMIN_PASSWORD == password


@app.errorhandler(404)
def page_not_found(error):
    return render_template('pagina_no_encontrada.html'), 404

@app.errorhandler(404)
def page_not_found(error):
    return render_template('pagina_no_encontrada.html'), 404

@app.route('/private')
def private():
    if 'user_id' not in flask_session:
        return redirect(url_for('login_get'))
    return render_template('private.html')

@app.route('/principal')
def principal():
    if 'user_id' not in flask_session:
        # Redirige al login si el usuario no está en sesión
        return redirect(url_for('login_get'))

    user_id = flask_session['user_id']  # Obtener el ID del usuario de la sesión

    with Session(engine) as session:
        # Primero, obtenemos los IDs de repositorios asociados con el usuario
        repo_ids = session.query(UserRepo.repo_id).filter(UserRepo.user_id == user_id).subquery()

        # Luego, hacemos un join con la tabla Repositorios usando los IDs obtenidos
        repositorios = session.query(Repositorios).join(repo_ids, Repositorios.id == repo_ids.c.repo_id).all()

        # Enviar los datos de los repositorios a la plantilla HTML
        return render_template('principal.html', repositorios=repositorios)


@app.get('/principal/add')
def add_get():
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para agregar elementos.")
        return redirect(url_for('login_get'))

    return render_template('add.html')


@app.post('/principal/add')
def add_post():
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
    response = requests.get(url)
    if response.status_code != 200:
        flash("El repositorio no existe en GitHub o está mal escrito.")
        return redirect(url_for('add_get'))

    repo_data = response.json()

    # Convertir las fechas a objetos de fecha
    fecha_ultima_actualizacion = datetime.strptime(repo_data['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date()
    fecha_creacion = datetime.strptime(repo_data['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()

    # Extraer datos adicionales
    num_stars = repo_data['stargazers_count']
    num_forks = repo_data['forks_count']
    default_branch = repo_data['default_branch']
    num_open_issues = repo_data['open_issues_count']

    with Session(engine) as session:
        try:
            # Verificar si el repositorio ya existe en la base de datos
            repositorio = session.query(Repositorios).filter_by(owner=owner, repo=repo_name).first()
            if repositorio:
                # Actualizar los datos existentes
                repositorio.fecha_ultima_actualizacion = fecha_ultima_actualizacion
                repositorio.num_stars = num_stars
                repositorio.num_forks = num_forks
                repositorio.default_branch = default_branch
                repositorio.num_open_issues = num_open_issues
            else:
                # Crear un nuevo registro si el repositorio no existe en la base de datos
                nuevo_repositorio = Repositorios(
                    owner=owner,
                    repo=repo_name,
                    fecha_ultima_actualizacion=fecha_ultima_actualizacion,
                    num_stars=num_stars,
                    num_forks=num_forks,
                    default_branch=default_branch,
                    num_open_issues=num_open_issues,
                    fecha_creacion=fecha_creacion,
                    favorito=False
                )
                session.add(nuevo_repositorio)
                session.flush()  # Obtener el ID del nuevo repositorio

                # Insertar una fila en la tabla user_repo
                user_id = flask_session['user_id']  # Obtener el ID del usuario actual
                user_repo = UserRepo(user_id=user_id, repo_id=nuevo_repositorio.id)
                session.add(user_repo)

            session.commit()
            flash("Repositorio añadido/actualizado exitosamente.")
        except SQLAlchemyError as e:
            session.rollback()
            flash("Error al añadir/actualizar el repositorio en la base de datos.")

    return redirect(url_for('detalles_get', owner=owner, repo=repo_name))



@app.get('/principal/detalles/<owner>/<repo>')
def detalles_get(owner, repo):
    if 'user_id' not in flask_session:
        flash("Por favor, inicia sesión para ver los detalles del repositorio.")
        return redirect(url_for('login_get'))

    with Session(engine) as session:
        repositorio = session.query(Repositorios).filter_by(owner=owner, repo=repo).first()
        if not repositorio:
            flash("Repositorio no encontrado.")
            return redirect(url_for('principal'))

    return render_template('detalles.html', repositorio=repositorio)

@app.post('/principal/detalles/<owner>/<repo>')
def detalles_post(owner, repo):
    if 'user_id' not in flask_session:
        return redirect(url_for('login_get'))

    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url)

    with Session(engine) as session:
        repositorio = session.query(Repositorios).filter_by(owner=owner, repo=repo).first()
        if not repositorio:
            flash("Repositorio no encontrado en la base de datos.")
            return redirect(url_for('principal'))

        if response.status_code != 200:
            flash(f"El repositorio {owner}/{repo} ya no está disponible en GitHub.")
            return redirect(url_for('detalles_get', owner=owner, repo=repo))

        repo_data = response.json()

        fecha_ultima_actualizacion = datetime.strptime(repo_data['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        fecha_creacion = datetime.strptime(repo_data['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()
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

    return redirect(url_for('detalles_get', owner=owner, repo=repo))

@app.route("/logout")
def logout():
    flask_session.pop('user_id',None)
    return redirect(url_for('login_get'))



