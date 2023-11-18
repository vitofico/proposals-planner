from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes, routes_wp, routes_company, routes_todo, routes_userpanel
