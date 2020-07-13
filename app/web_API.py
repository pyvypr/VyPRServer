"""
API functions for the web tool.
"""
from . import app_object, database
from flask import request, jsonify, render_template, send_file
from .utils import deserialise_property
import json


@app_object.route("/list_transactions/<function_id>/")
def list_transactions(function_id):
    return jsonify(data=database.list_transactions(function_id))


@app_object.route("/list_tests/")
def list_tests():
    tests = database.web_list_tests()
    return json.dumps(tests)


@app_object.route("/list_functions_by_tests/", methods=["GET", "POST"])
def list_functions_by_tests():
    data = json.loads(request.data)
    functions = database.web_list_functions(data)
    return json.dumps(functions)


@app_object.route("/list_function_calls/", methods=["GET", "POST"])
def list_function_calls():
    data = json.loads(request.data)
    function_id = data["function"]
    if data["tests"]!=[]:
        return jsonify(data=database.list_calls_from_id(function_id, data["tests"]))
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
    if request.data:
        request_dict = json.loads(request.data)
        ids_list = request_dict["ids"]
        property_hash = request_dict["property_hash"]
    else:
        ids_list = request.form.getlist('ids[]')
    data = database.get_calls_data(ids_list, property_hash)
    return json.dumps(data)


@app_object.route("/get_atom_type/<atom_index>/<inst_point_id>/")
def get_atom_type(atom_index, inst_point_id):
    atom_type = database.get_atom_type(atom_index, inst_point_id)
    return json.dumps(atom_type)


@app_object.route("/list_calls_between/", methods=["GET", "POST"])
def list_calls_between():
    start = json.loads(request.data)["from"]
    end = json.loads(request.data)["to"]
    id = json.loads(request.data)["function"]
    tests = json.loads(request.data)["tests"]
    if tests != []:
        list = database.list_calls_in_interval(start, end, id, tests)
    else:
        list = database.list_calls_in_interval(start, end, id)
    return json.dumps(list)


"""
All plotting functions first check for the existence of a precomputed plot.
If a plot is found, the data is returned along with the plot's identifying hash.
If no plot is found, the data is generated, then returned along with the newly generated identifying hash.
"""


@app_object.route("/get_plot_data_simple/", methods=["GET", "POST"])
def get_plot_data_simple():
    dict = json.loads(request.data)
    return_data = database.get_plot_data_simple(dict)
    return json.dumps(return_data)


@app_object.route("/get_plot_data_between/", methods=["GET", "POST"])
def get_plot_data_between():
    result_dict = json.loads(request.data)
    return_data = database.get_plot_data_between(result_dict)
    return json.dumps(return_data)


@app_object.route("/get_plot_data_mixed/", methods=["GET", "POST"])
def get_plot_data_mixed():
    result_dict = json.loads(request.data)
    return_data = database.get_plot_data_mixed(result_dict)
    return json.dumps(return_data)


@app_object.route("/get_plot_data_from_hash/<plot_hash>/", methods=["GET"])
def get_plot_data_from_hash(plot_hash):
    plot_data = database.get_plot_data_from_hash(plot_hash)
    return json.dumps(plot_data)


@app_object.route("/display_plot/<plot_hash>/", methods=["GET"])
def display_plot(plot_hash):
    """
    Given a uniquely identifying plot hash, return the plotting page to the user,
    which will render the plot in the same way as the inline case.
    """
    return render_template("plot.html", plot_hash=plot_hash)

@app_object.route("/download_plot/<plot_hash>/", methods=["GET"])
def download_plot(plot_hash):
    """
    Get the plot data, write it to a file and send it to the user.
    """
    filename = database.write_plot(plot_hash)
    return send_file("../generated_plots/%s" % filename, mimetype='application/pdf', as_attachment=True)

@app_object.route("/get_path_data_between/", methods=["GET", "POST"])
def get_path_data_between():
    result_dict = json.loads(request.data)
    return_data = database.get_path_data_between(result_dict)
    return json.dumps(return_data)
