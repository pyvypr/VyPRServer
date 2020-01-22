"""
Functions used as end points for the web-based analysis tool.
"""
from app import app_object
from flask import request, jsonify, render_template
from . import database
from .utils import deserialise_property_tree, deserialise_property


@app_object.route("/", methods=["get"])
def index():
    return render_template("index.html")


@app_object.route("/specification/", methods=["get"])
def specification():
    functions = database.web_list_functions()
    # process the property serialisation for each function to turn it into an understandable string
    # representation of the property

    print(functions)

    functions = deserialise_property_tree(functions)

    return render_template("by_specification.html", functions=json.dumps(functions))


@app_object.route("/verdict/", methods=["get"])
def verdict():
    functions = deserialise_property_tree(database.web_list_functions())
    return render_template("by_verdict.html", functions=json.dumps(functions))


@app_object.route("/about/", methods=["get"])
def about():
    return render_template("about.html")


@app_object.route("/list_http_requests/<function_id>/")
def list_http_requests(function_id):
    return jsonify(data=database.list_http_requests(function_id))


@app_object.route("/list_function_calls/<http_request_id>/<function_name>/")
def list_function_calls(http_request_id, function_name):
    return jsonify(data=database.list_calls_during_request(http_request_id, function_name))


@app_object.route("/list_verdicts/<function_call_id>/")
def list_verdicts(function_call_id):
    return jsonify(data=database.list_verdicts_from_function_call(function_call_id))


@app_object.route("/list_function_calls_from_verdicts/<verdict>/<path>/")
def list_function_calls_from_verdict_and_path(verdict, path):
    map_structure = database.get_http_request_function_call_pairs(verdict, path)
    # now, deserialise the property descriptions
    for function_id in map_structure["functions"].keys():
        map_structure["functions"][function_id]["property"] = deserialise_property(
            map_structure["functions"][function_id]["property"])

    # now, send the map into a template and return the html

    template_with_data = render_template("function_list.html", data=map_structure,
                                         truth_map={1: "Satisfaction", 0: "Violation"})

    return template_with_data