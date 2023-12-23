from sqlalchemy.exc import IntegrityError
from flask import Flask, flash, redirect, render_template, request, session as flask_session, url_for
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
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(30), unique=True)
    repo: Mapped[str] = mapped_column(String(30), unique=True)
    fecha_ultima_actualizacion: Mapped[date] = Column(Date)
    favorito: Mapped[Optional[bool]]
    


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
    if len(request.form['username']) != 0 and len(request.form['password']) != 0:
        with Session(engine) as session:
            try:
                usuario = User(
                    username=request.form['username'],
                    password=request.form['password'])

                session.add(usuario)
                session.commit()
                flask_session['logged_in_user'] = usuario.username
                flash('Te has registrado satisfactoriamente')
                return redirect(url_for('principal'))
            except IntegrityError as e:
                # Captura la excepción de integridad y maneja el caso de usuario duplicado
                session.rollback()
                flash('Error al registrar: El nombre de usuario ya está en uso. Por favor, elige otro.')
    else:
        flash('Usuario o contraseña no correcto')

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


@app.route('/principal/add')
def add():
    if 'logged_in_user' not in flask_session:
        return redirect(url_for('login_get'))

    return render_template('add.html')


@app.route('/principal/detalles/<owner>/<repo>')
def detalles(owner, repo):
    if 'logged_in_user' not in flask_session:
        return redirect(url_for('login_get'))
    
    return render_template('detalles.html', owner=owner, repo=repo)

@app.route("/logout")
def logout():
    flask_session.pop('logged_in_user',None)
    return redirect(url_for('login_get'))



