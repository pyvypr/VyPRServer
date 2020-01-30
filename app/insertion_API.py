"""
Verdict storage end points for use by the VyPR monitoring machinery.
"""
from app import app_object
from flask import request, jsonify, render_template
from . import database
import json


@app_object.route("/register_verdicts/", methods=["post"])
def register_verdicts():
    """
    Receives a verdict from a monitored service, and stores it
    """
    print("attempting verdict insertion")
    print(request.data)

    verdict_data = json.loads(request.data)

    print("attempting verdict insertion for data %s" % str(verdict_data))

    database.insert_verdicts(verdict_data)

    print("verdicts inserted")

    return "success"


@app_object.route("/insert_function_call_data/", methods=["post"])
def insert_function_call_data():
    """
    Receives a json list of condition ids that make up the program path for a given function run.
    This is inserted into the database so that mapping observations
    to the appropriate previous condition is straightforward
    (we just have to follow the chain for the correct number of steps).
    """
    call_data = json.loads(request.data)
    insertion_result = database.insert_function_call_data(call_data)
    return json.dumps(insertion_result)


@app_object.route("/store_property/", methods=["post"])
def store_property():
    """
    Receives a serialised property and stores it, with its hash.
    Note: the hash stored must be the same as the one given to the instruments in the
    monitored code.
    """
    property_data = json.loads(request.data)

    print(property_data)
    print("attempting property insertion")
    atom_index_to_db_index, function_id = database.insert_property(property_data)
    print("property inserted")

    return json.dumps({"atom_index_to_db_index": atom_index_to_db_index, "function_id": function_id})


@app_object.route("/store_binding/", methods=["post"])
def store_binding():
    """
    Receives a serialised binding and stores it.
    """
    binding_data = json.loads(request.data)

    print(binding_data)
    print("attempting binding insertion")
    new_id = database.insert_binding(binding_data)
    print("binding inserted")

    return str(new_id)


@app_object.route("/store_instrumentation_point/", methods=["post"])
def store_instrumentation_point():
    """
    Receives a serialised instrumentation point, with branch condition sequence and path length data,
    and stores it.
    Note: this returns an ID which instrumentation then attaches to an instrument
    so we can determine which instrumentation point in the SCFG generated observations at runtime.
    """
    instrumentation_point_data = json.loads(request.data)
    print(instrumentation_point_data)
    print("attempting instrumentation point insertion")
    new_id = database.insert_instrumentation_point(instrumentation_point_data)
    print("instrumentation point inserted")

    return str(new_id)


@app_object.route("/store_branching_condition/", methods=["post"])
def store_branching_condition():
    """
    Receives a serialised branching condition.
    Note: this returns an ID which instrumentation then attaches to branch recording instruments.
    """
    branching_condition_data = json.loads(request.data)
    print(branching_condition_data)
    print("attempting branching condition insertion")
    new_id = database.insert_branching_condition(branching_condition_data)
    print("branching condition inserted or already existed")

    return str(new_id)
