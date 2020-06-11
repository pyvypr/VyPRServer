"""
Functions used as end points for the web-based analysis tool.
"""
from . import app_object, database
from flask import render_template
import json


@app_object.route("/", methods=["get"])
def index():
    functions = database.web_list_functions()
    # process the property serialisation for each function to turn it into an understandable string
    # representation of the property
    return render_template("by_specification_vue.html", functions=json.dumps(functions))
