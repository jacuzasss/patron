from config import Config
from copy import deepcopy
from datetime import datetime
from flask import Flask, flash, redirect, url_for
from flask_blogging import BloggingEngine, SQLAStorage
from flask_blogging.signals import editor_post_saved
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_principal import Permission, RoleNeed
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config.from_object(Config)

# extensions
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
sql_storage = SQLAStorage(db=db)
db.create_all()
blog_engine = BloggingEngine(app, sql_storage)
login = LoginManager(app)
mail = Mail(app)

# permissions - flask_principal objects created by BloggingEngine
principals = blog_engine.principal
admin_permission = Permission(RoleNeed('admin'))

# blueprints
from app.api import bp as api_bp
from app.auth import bp as auth_bp
from app.admin import bp as admin_bp
from app.main import bp as main_bp
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(main_bp)

# deepcopy auto-generated flask_blogging bp, then delete it
blogging_bp = deepcopy(app.blueprints['blogging'])
del app.blueprints['blogging']


# modify deepcopied flask_blogging bp
@blogging_bp.before_request
def protect():
    if current_user.is_authenticated:
        if datetime.today() <= current_user.expiration:
            return None
        else:
            flash('You must have a paid-up subscription \
                  to view updates.')
            return redirect(url_for('auth.account'))
    else:
        flash('Please login to view updates.')
        return redirect(url_for('auth.login'))

# register modified flask_blogging bp
app.register_blueprint(blogging_bp, url_prefix=app.config.get('BLOGGING_URL_PREFIX')) 

# subscribe to new post signal from blog_engine
from app.email import email_post
@editor_post_saved.connect
def email(sender, post):
    email_post(post)

from app import models
