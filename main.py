from application import app, api
from Controllers.MainController import MainController
from Controllers.TrackingController import TrackingController
from Controllers.AnalyticsController import AnalyticsController

if __name__ == '__main__':
    """
    Запуск приложения в режиме отладки
    """

    api.add_resource(MainController)
    api.add_resource(TrackingController)
    api.add_resource(AnalyticsController)
    
    app.run(debug=True, port=3000, host='127.0.0.1')
    
