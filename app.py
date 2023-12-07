from flask import Flask, flash, redirect, render_template, request, session, url_for
from markupsafe import escape

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route("/")
def home():
    return render_template('bienvenido.html')



@app.route("/register")   
def register():
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
    username = request.form['username']
    password = request.form['password']
    if authenticate(username, password):
        session['logged_in_user'] = username
        flash('Te has logueado satisfactoriamente')
        return redirect(url_for('private'))
    else:
        error = 'Invalid username/password'
    return render_template(
        'login.html', 
        error=error, 
        username = username
    )

    

def authenticate(username, password):
    #TODO: Autenticar a un usuario con una base de datos
    return ADMIN_USERNAME == username and ADMIN_PASSWORD == password


@app.errorhandler(404)
def page_not_found(error):
    return render_template('pagina_no_encontrada.html'), 404


@app.route('/private')
def private():
    if 'logged_in_user' not in session:
        return redirect(url_for('login_get'))
    return render_template('private.html')


@app.route("/logout")
def logout():
    session.pop('logged_in_user',None)
    return redirect(url_for('login_get'))
