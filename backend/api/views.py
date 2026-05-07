"""页面路由"""
from flask import Blueprint, render_template

view_bp = Blueprint('views', __name__)


@view_bp.route('/')
def index():
    return render_template('index.html')


@view_bp.route('/<path:path>')
def catch_all(path):
    return render_template('index.html')
