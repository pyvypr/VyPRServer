"""
API functions for the web tool.
"""
from . import app_object, database
from flask import request, jsonify, render_template
from .utils import deserialise_property
import json


@app_object.route("/list_transactions/<function_id>/")
def list_transactions(function_id):
    return jsonify(data=database.list_transactions(function_id))


@app_object.route("/list_function_calls/<function_id>/")
def list_function_calls(function_id):
    return jsonify(data=database.list_calls_from_id(function_id))


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


@app_object.route("/get_source_code/<function_id>/")
def get_source_code(function_id):
    code_dict = database.get_code(function_id)
    return json.dumps(code_dict)


@app_object.route("/get_function_calls_data/",methods=["GET", "POST"])
def get_function_calls_data():
    if (request.data):
        ids_list = json.loads(request.data)["ids"]
    else:
        ids_list = request.form.getlist('ids[]')
    data = database.get_calls_data(ids_list)
    return json.dumps(data)


@app_object.route("/get_atom_type/<atom_index>/<inst_point_id>/")
def get_atom_type(atom_index, inst_point_id):
    atom_type = database.get_atom_type(atom_index, inst_point_id)
    return json.dumps(atom_type)


@app_object.route("/get_plot_data_simple/", methods=["GET", "POST"])
def get_plot_data_simple():
    dict = json.loads(request.data)
    return_data = database.get_plot_data_simple(dict)
    return json.dumps(return_data)

@app_object.route("/list_calls_between/", methods=["GET", "POST"])
def list_calls_between():
    start = json.loads(request.data)["from"]
    end = json.loads(request.data)["to"]
    id = json.loads(request.data)["function"]
    list = database.list_calls_in_interval(start, end, id)
    return json.dumps(list)

@app_object.route("/get_plot_data_between/", methods=["GET", "POST"])
def get_plot_data_between():
    dict = json.loads(request.data)
    return_data = database.get_plot_data_between(dict)
    print(return_data)
    return json.dumps(return_data)
