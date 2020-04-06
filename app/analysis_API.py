"""
Functions that make up the analysis API.
"""
from app import app_object
from . import database
import json
from flask import request


"""
Endpoint which shuts down the server
"""
@app_object.route("/shutdown/", methods=['GET'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()






"""
Queries based on paths.
"""


@app_object.route("/client/get_parametric_path/", methods=["POST"])
def get_parametric_path():
    data = json.loads(request.get_data())
    observation_ids = data["observation_ids"]
    instrumentation_point_id = data["instrumentation_point_id"]

    intersection_data = database.compute_intersection(observation_ids, instrumentation_point_id)

    return json.dumps(intersection_data)


@app_object.route("/client/get_path_condition_sequence/<observation_id>/", methods=["GET"])
def get_path_condition_sequence(observation_id):
    return json.dumps(database.compute_condition_sequence_and_path_length(observation_id))

"""
Queries based on the function table.
"""


@app_object.route("/client/function/")
def list_functions():
    return database.list_functions()


@app_object.route("/client/function/id/<function_id>/transaction/id/<transaction_id>/function_calls/")
def list_function_calls_transaction_id(transaction_id, function_id):
    return database.list_calls_transactionid(transaction_id, function_id)


@app_object.route("/client/function/name/<function_name>/")
def get_function_by_name(function_name):
    return database.get_f_byname(function_name)


@app_object.route("/client/function/name/<function_name>/function_calls/")
def get_function_calls_from_function_name(function_name):
    return database.list_calls_function(function_name)


@app_object.route("/client/function/id/<function_id>/")
def get_function_by_id(function_id):
    return database.get_f_byid(function_id)


@app_object.route("/client/function/id/<id>/bindings/")
def get_bindings_from_function_property_pair(id):
    return database.get_bindings_from_function_property_pair(id)


@app_object.route("/client/function/id/<function_id>/verdicts/")
def list_verdicts_of_function(function_id):
    return database.list_verdicts_of_function(function_id)


@app_object.route("/client/function/id/<function_id>/verdict/value/<verdict_value>/")
def list_verdicts_of_function_with_value(function_id, verdict_value):
    return database.list_verdicts_of_function_with_value(function_id, verdict_value)


"""
Queries based on the transaction table.
"""


@app_object.route("/client/transaction/id/<transaction_id>/function_calls/")
def list_function_calls_transaction(transaction_id):
    return database.list_calls_transaction(transaction_id)


@app_object.route("/client/transaction/id/<transaction_id>/")
def get_transaction_by_id(transaction_id):
    return database.get_transaction_byid(transaction_id)


@app_object.route("/client/transaction/time/<time_of_request>/")
def get_transaction_by_time(time_of_request):
    return database.get_transaction_bytime(time_of_request)

@app_object.route("/client/transaction/time/between/<lower_bound>/<upper_bound>/")
def get_transaction_in_interval(lower_bound, upper_bound):
    return database.get_transaction_in_interval(lower_bound, upper_bound)


"""
Queries based on the function_call table.
"""


@app_object.route("/client/function_call/id/<call_id>/")
def get_call_by_id(call_id):
    return database.get_call_byid(call_id)


@app_object.route("/client/function_call/id/<call_id>/verdicts/")
def list_verdicts_of_call(call_id):
    return database.list_verdicts_call(call_id)


@app_object.route("/client/function_call/id/<call_id>/observations/")
def list_observations_during_call(call_id):
    return database.list_observations_call(call_id)


@app_object.route("/client/function_call/id/<call_id>/verdict/value/<verdict_value>/")
def list_verdicts_with_value_of_call(call_id, verdict_value):
    return database.list_verdicts_with_value_of_call(call_id, verdict_value)


"""
Queries based on the verdict table.
"""


@app_object.route("/client/verdict/id/<verdict_id>/")
def get_verdict_by_id(verdict_id):
    return database.get_verdict_byid(verdict_id)


@app_object.route("/client/verdict/id/<verdict_id>/observations/")
def get_observations_from_verdict(verdict_id):
    return database.get_observations_from_verdict(verdict_id)


"""
Queries based on the atom table.
"""


@app_object.route("/client/atom/id/<atom_id>/")
def get_atom_by_id(atom_id):
    return database.get_atom_byid(atom_id)


@app_object.route("/client/atom/index/<atom_index>/property/<property_hash>/")
def get_atom_by_index_and_property(atom_index, property_hash):
    return database.get_atom_by_index_and_property(atom_index, property_hash)


"""
Queries based on the property table.
"""


@app_object.route("/client/property/hash/<hash>/")
def get_property_by_hash(hash):
    return database.get_property_byhash(hash)


"""
Queries based on the instrumentation_point table.
"""


@app_object.route("/client/instrumentation_point/id/<point_id>/")
def get_instrumentation_point_by_id(point_id):
    return database.get_point_byid(point_id)


@app_object.route("/client/instrumentation_point/id/<point_id>/observations/")
def list_observations_of_point(point_id):
    return database.list_observations_of_point(point_id)


"""
Queries based on the binding table.
"""


@app_object.route("/client/binding/id/<binding_id>/")
def get_binding_by_id(binding_id):
    return database.get_binding_byid(binding_id)


@app_object.route("/client/binding/id/<binding_id>/verdicts/")
def list_verdicts_from_binding(binding_id):
    return database.list_verdicts_from_binding(binding_id)


"""
Queries based on the observation table.
"""


@app_object.route("/client/observation/id/<observation_id>/")
def get_observation_by_id(observation_id):
    return database.get_observation_byid(observation_id)


@app_object.route("/client/observation/id/<observation_id>/assignments/")
def list_assignments_given_observation(observation_id):
    return database.list_assignments_obs(observation_id)


@app_object.route("/client/observation/")
def list_observations():
    return database.list_observations()


"""
Queries based on the assignment table.
"""


@app_object.route("/client/assignment/id/<assignment_id>/")
def get_assignment_by_id(assignment_id):
    return database.get_assignment_byid(assignment_id)


"""
Queries based on the path_condition table.
"""


@app_object.route("/client/path_condition/id/<pathcon_id>/")
def get_path_condition_by_id(pathcon_id):
    return database.get_pathcon_byid(pathcon_id)


"""
Queries based on the path_condition_structure table.
"""


@app_object.route("/client/path_condition_structure/id/<pcs_id>/")
def get_path_condition_structure_by_id(pcs_id):
    return database.get_pcs_byid(pcs_id)


@app_object.route("/client/path_condition_structure/function_call/<call_id>/")
def get_path_conditions_by_function_call_id(call_id):
    return database.get_path_conditions_by_function_call_id(call_id)
