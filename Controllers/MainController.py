from application import app
from flask import jsonify, request, render_template
from flask_restful import Resource

class MainController(Resource):

    """
    Главный контроллер для обработки основных маршрутов приложения.
    """

    @staticmethod
    @app.route('/')
    def index():
        return render_template('index.html')

