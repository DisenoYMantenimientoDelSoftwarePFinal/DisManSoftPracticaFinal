import requests
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask import Flask, flash, redirect, render_template, request, session as flask_session, url_for
from sqlalchemy import Column, Integer, String, Boolean, Date
from datetime import datetime


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
    owner = Column(String(30), unique=True)
    repo = Column(String(30), unique=True)
    fecha_ultima_actualizacion = Column(Date)
    favorito = Column(Boolean, default=False)
    num_forks = Column(Integer, default=0, nullable=True)
    num_stars = Column(Integer, default=0, nullable=True)
    default_branch = Column(String(50))
    num_open_issues = Column(Integer, default=0)
    fecha_creacion = Column(Date)
    


engine = create_engine("sqlite:///./BD/githubExplorer.sqlite", echo=True)
Base.metadata.create_all(engine)

from sqlalchemy.orm import Session




app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

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
    if len(username) == 0 or len(password) < 6:  # Ejemplo: longitud mínima de contraseña de 8
        flash('Usuario o contraseña no válidos')
        return render_template('register.html')

    hashed_password = generate_password_hash(password)

    with Session(engine) as session:
        try:
            usuario = User(username=username, password=hashed_password)

            session.add(usuario)
            session.commit()
            flask_session['logged_in_user'] = usuario.username
            flash('Te has registrado satisfactoriamente')
            return redirect(url_for('principal'))
        except IntegrityError as e:
            session.rollback()
            # Aquí puedes realizar una verificación más específica del error si es necesario
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
    username = ''
    password = ''
    with Session(engine) as session:
        result = session.scalars(
            select(
                User,
            ).where(
                User.username == request.form['username']
            ).where(
                User.password == request.form['password'])
        )
        usuario = result.first()
        if usuario is not None:
            flask_session['logged_in_user'] = usuario.username
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
    if 'logged_in_user' not in flask_session:
        return redirect(url_for('login_get'))
    return render_template('private.html')

@app.route('/principal')
def principal():
    if 'logged_in_user' not in flask_session:
        return redirect(url_for('login_get'))
    
    
    return render_template('principal.html')


@app.get('/principal/add')
def add_get():
    if 'logged_in_user' not in flask_session:
        flash("Por favor, inicia sesión para agregar elementos.")
        return redirect(url_for('login_get'))

    return render_template('add.html')


@app.post('/principal/add')
def add_post():
    if 'logged_in_user' not in flask_session:
        flash("Por favor, inicia sesión para agregar repositorios.")
        return redirect(url_for('login_get'))

    repo_input = request.form['repositorio']  # Espera entrada en formato "owner/repo"
    owner, repo_name = repo_input.split('/')

    # Utiliza la API de GitHub para obtener datos del repositorio
    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    response = requests.get(url)
    if response.status_code != 200:
        flash("Error al obtener datos del repositorio desde GitHub.")
        return redirect(url_for('add'))

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
            # Verificar si el repositorio ya existe
            repositorio = session.query(Repositorios).filter_by(owner=owner, repo=repo_name).first()
            if repositorio:
                # Actualizar los datos existentes
                repositorio.fecha_ultima_actualizacion = fecha_ultima_actualizacion
                repositorio.num_stars = num_stars
                repositorio.num_forks = num_forks
                repositorio.default_branch = default_branch
                repositorio.num_open_issues = num_open_issues
            else:
                # Crear un nuevo registro
                nuevo_repositorio = Repositorios(
                    owner=owner,
                    repo=repo_name,
                    fecha_ultima_actualizacion=fecha_ultima_actualizacion,
                    num_stars=num_stars,
                    num_forks=num_forks,
                    default_branch=default_branch,
                    num_open_issues=num_open_issues,
                    fecha_creacion=fecha_creacion,
                    favorito=False  # valor predeterminado, cambia según sea necesario
                )
                session.add(nuevo_repositorio)

            session.commit()
            flash("Repositorio añadido/actualizado exitosamente.")
        except SQLAlchemyError as e:
            session.rollback()
            flash("Error al añadir/actualizar el repositorio en la base de datos.")

    return redirect(url_for('detalles_get', owner=owner, repo=repo_name))

@app.get('/principal/detalles/<owner>/<repo>')
def detalles_get(owner, repo):
    if 'logged_in_user' not in flask_session:
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
    if 'logged_in_user' not in flask_session:
        return redirect(url_for('login_get'))

    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url)
    if response.status_code != 200:
        return redirect(url_for('detalles_get', owner=owner, repo=repo))

    repo_data = response.json()

    fecha_ultima_actualizacion = datetime.strptime(repo_data['updated_at'], '%Y-%m-%dT%H:%M:%SZ').date()
    num_stars = repo_data['stargazers_count']
    num_forks = repo_data['forks_count']
    default_branch = repo_data['default_branch']
    num_open_issues = repo_data['open_issues_count']

    with Session(engine) as session:
        repositorio = session.query(Repositorios).filter_by(owner=owner, repo=repo).first()
        if not repositorio:
            return redirect(url_for('principal'))

        repositorio.fecha_ultima_actualizacion = fecha_ultima_actualizacion
        repositorio.num_stars = num_stars
        repositorio.num_forks = num_forks
        repositorio.default_branch = default_branch
        repositorio.num_open_issues = num_open_issues

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            return redirect(url_for('detalles_get', owner=owner, repo=repo))

    return redirect(url_for('detalles_get', owner=owner, repo=repo))

@app.route("/logout")
def logout():
    flask_session.pop('logged_in_user',None)
    return redirect(url_for('login_get'))



