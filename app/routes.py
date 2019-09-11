"""
Module to define the routes in this test service.
"""

from app import app_object
import datetime
from flask import request, jsonify, render_template
import json
import pickle
import database
import sys
from analysis_API import *

from VyPR.formula_building.formula_building import *
from VyPR.monitor_synthesis.formula_tree import *

"""
Utility functions - these should be moved to another module.
"""

def friendly_bind_variable(bind_variable):
	if type(bind_variable) is StaticState:
		return "Forall(%s = changes(%s)).\\" % (bind_variable._bind_variable_name, bind_variable._name_changed)
	elif type(bind_variable) is StaticTransition:
		return "Forall(%s = calls(%s)).\\" % (bind_variable._bind_variable_name, bind_variable._operates_on)

def friendly_atom(atom):
	if type(atom) is TransitionDurationInInterval:
		return "%s.duration()._in((%s, %s))" % (atom._transition, atom._interval[0], atom._interval[1])
	elif type(atom) is StateValueInInterval:
		return "%s(%s)._in((%s, %s))" % (atom._state, atom._name, atom._interval[0], atom._interval[1])
	elif type(atom) is StateValueInOpenInterval:
		return "%s <= value of %s in %s <= %s" % (atom._interval[0], atom._name, atom._state, atom._interval[1])
	elif type(atom) is StateValueEqualTo:
		return "value of %s in %s = %s" % (atom._name, atom._state, atom._value)

def get_bind_variable_names(bind_variables):
	return map(lambda bind_variable : bind_variable._bind_variable_name, bind_variables)

def friendly_variable_in_formula(variable):
	return "%s" % variable._bind_variable_name

def deserialise_property_tree(property_tree, path=[]):
	"""
	recurse on the property tree to deserialise the properties that are stored there.
	"""
	if len(path) == 0:
		# we're at the root
		for key in property_tree.keys():
			property_tree[key] = deserialise_property_tree(property_tree, [key])

		return property_tree
	else:
		# we have a path, so go down to the subtree
		subtree = property_tree[path[0]]
		for item in path[1:]:
			subtree = subtree[item]

		if type(subtree) is tuple:
			# if the subtree is just a tuple, we're at a leaf
			subtree = list(subtree)
			property_dictionary = json.loads(subtree[3])
			TransitionDurationInInterval.__repr__ = friendly_atom
			StaticState.__repr__ = friendly_variable_in_formula
			StaticTransition.__repr__ = friendly_variable_in_formula
			subtree.append(str(pickle.loads(property_dictionary["property"])))
			subtree.append("%s" % ", ".join(map(friendly_bind_variable, pickle.loads(property_dictionary["bind_variables"]).values())))
			subtree.append(", ".join(get_bind_variable_names(pickle.loads(property_dictionary["bind_variables"]).values())))

			return subtree
		elif type(subtree) is list:
			for n in range(len(subtree)):
				subtree[n] = deserialise_property_tree(property_tree, path + [n])
			return subtree
		else:
			# if not, we have a further subtree
			for next_item in subtree.keys():
				subtree[next_item] = deserialise_property_tree(property_tree, path + [next_item])

			return subtree

def deserialise_property(dictionary):
	"""
	Given the bind variables and formula of a property, use the classes from VyPR to deserialise it and
	form its string representation.
	"""
	# override the string representation methods
	TransitionDurationInInterval.__repr__ = friendly_atom
	StaticState.__repr__ = friendly_variable_in_formula
	StaticTransition.__repr__ = friendly_variable_in_formula

	# deserialise
	return {
		"property" : str(pickle.loads(dictionary["property"])),
		"bind_variables" : "%s" % ", ".join(map(friendly_bind_variable, pickle.loads(dictionary["bind_variables"]).values())),
		"bind_variable_names" : ", ".join(get_bind_variable_names(pickle.loads(dictionary["bind_variables"]).values()))
	}

"""
Verdict storage end points for use by the VyPR monitoring machinery.
"""

@app_object.route("/register_verdict/", methods=["post"])
def register_verdict():
	"""
	Receives a verdict from a monitored service, and stores it
	"""
	verdict_data = json.loads(request.data)
	verdict_data["verdict"] = json.loads(verdict_data["verdict"])

	print("attempting verdict insertion for data %s" % str(verdict_data))

	database.insert_verdict(verdict_data)

	print("verdict inserted")

	return "success"

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

	return json.dumps({"atom_index_to_db_index" : atom_index_to_db_index, "function_id" : function_id})

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

"""
Functions used as end points for the web-based analysis tool.
"""

@app_object.route("/", methods=["get"])
def index():
	return render_template("index.html")

@app_object.route("/specification/", methods=["get"])
def specification():
	functions = database.list_functions()
	# process the property serialisation for each function to turn it into an understandable string
	# representation of the property

	functions = deserialise_property_tree(functions)

	return render_template("by_specification.html", functions=json.dumps(functions))

@app_object.route("/verdict/", methods=["get"])
def verdict():
	functions = deserialise_property_tree(database.list_functions())
	return render_template("by_verdict.html", functions=json.dumps(functions))

@app_object.route("/about/", methods=["get"])
def about():
	return render_template("about.html")

@app_object.route("/list_http_requests/<function_id>/")
def list_http_requests(function_id):
	return jsonify(database.list_http_requests(function_id))

@app_object.route("/list_function_calls/<http_request_id>/<function_name>/")
def list_function_calls(http_request_id, function_name):
	return jsonify(database.list_calls_during_request(http_request_id, function_name))

@app_object.route("/list_verdicts/<function_call_id>/")
def list_verdicts(function_call_id):
	return jsonify(database.list_verdicts_from_function_call(function_call_id))

@app_object.route("/list_function_calls_from_verdicts/<verdict>/<path>/")
def list_function_calls_from_verdict_and_path(verdict, path):
	map_structure = database.get_http_request_function_call_pairs(verdict, path)
	# now, deserialise the property descriptions
	for function_id in map_structure["functions"].keys():
		map_structure["functions"][function_id]["property"] = deserialise_property(map_structure["functions"][function_id]["property"])

	# now, send the map into a template and return the html

	template_with_data = render_template("function_list.html", data=map_structure, truth_map={1:"Satisfaction", 0:"Violation"})

	return template_with_data

"""
Functions used as end points for VyPR-analysis.
"""

@app_object.route("/get_parametric_path/", methods=["POST"])
def get_parametric_path():
	"""
	A list of observation IDs, along with an instrumentation point ID, will be given in the request body.
	"""
	data = json.loads(request.get_data())
	observation_ids = data["observation_ids"]
	instrumentation_point_id = data["instrumentation_point_id"]

	print("getting intersection of paths up to observations with IDs %s, based on instrumentation point with ID %i" %\
		(str(observation_ids), instrumentation_point_id))

	intersection_data = database.compute_intersection(observation_ids, instrumentation_point_id)

	return json.dumps(intersection_data)
