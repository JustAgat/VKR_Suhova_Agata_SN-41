from application import app
from flask import jsonify, request, render_template, session
from flask_restful import Resource
from Controllers.AuthController import login_required
from Models.Site import Site

class MainController(Resource):

    """
    Главный контроллер для обработки основных маршрутов приложения.
    """

    @staticmethod
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/analytics')
    def analytics_dashboard():
        return render_template('analytics.html')

    @staticmethod
    @app.route('/analytics/<site_id>')
    @login_required
    def analytics_site(site_id):
        site = Site.query.filter_by(id=site_id, user_id=session['user_id']).first_or_404()
        return render_template('analytics.html', site=site)
    
