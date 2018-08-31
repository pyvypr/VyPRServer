from flask import Flask

# setup the application object
app_object = Flask(__name__)

from app import routes