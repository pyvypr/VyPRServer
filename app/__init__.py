from flask import Flask
from flask_cors import CORS

# setup the application object
app_object = Flask(__name__)

# allow cross origin requests
app_object.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app_object)

# set up central configuration variables
database_string = "verdicts.db"
monitored_service_path = None
events_database_string = "events.db"

# import routes
from . import routes
