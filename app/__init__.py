from flask import Flask

# setup the application object
app_object = Flask(__name__)
database_string = "verdicts.db"
monitored_service_path = None

from app import routes
