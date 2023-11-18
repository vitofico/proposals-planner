import logging
import os
from logging.handlers import SMTPHandler, RotatingFileHandler

import rq
from elasticsearch import Elasticsearch
from flask import Flask, request, current_app
from flask_admin import Admin
from flask_babel import Babel, lazy_gettext as _l
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from flask_apscheduler import APScheduler
from config import Config
from flask_jsglue import JSGlue


jsglue = JSGlue()
db = SQLAlchemy ()
migrate = Migrate ()
login = LoginManager ()
login.login_view = 'auth.login'
login.login_message = _l ('Please log in to access this page.')
mail = Mail ()
bootstrap = Bootstrap ()
moment = Moment ()
babel = Babel ()
admin = Admin (name='Nous', template_mode='bootstrap4')
scheduler = APScheduler()

def create_app(config_class=Config):
    app = Flask (__name__)
    app.config.from_object (config_class)
    db.init_app (app)
    migrate.init_app (app, db)
    login.init_app (app)
    mail.init_app (app)
    bootstrap.init_app (app)
    moment.init_app (app)
    babel.init_app (app)
    admin.init_app (app)
    jsglue.init_app(app)
    # scheduler.init_app (app)
    # scheduler.start ()

    db.app = app

    app.elasticsearch = Elasticsearch ([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None
    app.redis = Redis.from_url (app.config['REDIS_URL'])
    app.task_queue = rq.Queue ('nostradamus-tasks', connection=app.redis)

    from app.errors import bp as errors_bp
    app.register_blueprint (errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint (auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint (main_bp)

    from app.api import bp as api_bp
    app.register_blueprint (api_bp, url_prefix='/api')

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler (
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Website Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel (logging.ERROR)
            app.logger.addHandler (mail_handler)

        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler ()
            stream_handler.setLevel (logging.INFO)
            app.logger.addHandler (stream_handler)
        else:
            if not os.path.exists ('logs'):
                os.mkdir ('logs')
            file_handler = RotatingFileHandler ('logs/website.log',
                                                maxBytes=10240, backupCount=10)
            file_handler.setFormatter (logging.Formatter (
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel (logging.INFO)
            app.logger.addHandler (file_handler)

        app.logger.setLevel (logging.INFO)
        app.logger.info ('Website startup')

    return app


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match (current_app.config['LANGUAGES'])


from app import models
from app.custom_libs.utilities_lib import MyModelView

admin.add_view (MyModelView (models.User, db.session))
admin.add_view (MyModelView (models.Proposal, db.session))
admin.add_view (MyModelView (models.Company, db.session))
admin.add_view (MyModelView (models.WP, db.session))
admin.add_view (MyModelView (models.Deliverable, db.session))
admin.add_view (MyModelView (models.ProposalStatus, db.session))
admin.add_view (MyModelView (models.Association, db.session))
admin.add_view (MyModelView (models.WP_Company, db.session))
admin.add_view (MyModelView (models.ToDo, db.session))
