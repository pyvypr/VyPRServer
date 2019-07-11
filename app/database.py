"""
Module to handle interaction with the verdict database.
"""

# use sqlite for now
import sqlite3
import traceback
import json
import sys
import ast
import os
from graphviz import Digraph
import pickle

database_string = "verdicts.db"

sys.path.append("VyPR/")

from control_flow_graph.construction import CFG
from control_flow_graph.parse_tree import ParseTree

def get_connection():
	# for now, let exceptions appear in the log
	global database_string
	return sqlite3.connect(database_string)

def insert_verdict(verdict_dictionary):
	"""
	Given a verdict dictionary containing a function name,
	time of call, bind space index and verdict (paired with timestamp),
	insert the necessary rows into the tables in the verdict schema.
	"""

	connection = get_connection()
	cursor = connection.cursor()
	# find if the function exists in the database
	results = cursor.execute("select * from function where fully_qualified_name = ? and property = ?", [verdict_dictionary["function_name"], verdict_dictionary["property_hash"]]).fetchall()
	new_function_id = int(results[0][0])

	# create the binding if it doesn't already exist
	results = cursor.execute("select * from binding where binding_space_index = ? and function = ?", [verdict_dictionary["bind_space_index"], new_function_id]).fetchall()
	new_binding_id = int(results[0][0])

	# create the http request
	results = cursor.execute("select * from http_request where time_of_request = ?", [verdict_dictionary["http_request_time"]]).fetchall()
	if len(results) == 0:
		# no binding exists yet, so insert a new binding
		cursor.execute("insert into http_request (time_of_request, grouping) values (?, ?)",
			(verdict_dictionary["http_request_time"], ""))
		connection.commit()
		# get the id
		new_http_request_id = int(cursor.execute("select id from http_request where time_of_request = ?", [verdict_dictionary["http_request_time"]]).fetchall()[0][0])
	else:
		# get the id of the existing http request
		new_http_request_id = int(results[0][0])

	print("verdict data received")
	print(verdict_dictionary["verdict"])

	# insert the function call that the verdict belongs to
	results = cursor.execute("select * from function_call where time_of_call = ? and function = ?", [verdict_dictionary["time_of_call"], new_function_id]).fetchall()
	if len(results) == 0:
		# no binding exists yet, so insert a new binding
		cursor.execute("insert into function_call (function, time_of_call, http_request) values (?, ?, ?)",
			(new_function_id, verdict_dictionary["time_of_call"], new_http_request_id))
		new_function_call_id = cursor.lastrowid
		connection.commit()
	else:
		# get the id of the existing function call
		new_function_call_id = int(results[0][0])

	# now we have a verdict to link observations to, we insert the assignments and the observations
	# process the slice dictionary received and, for any assignment not already existing, create a new one.
	# keeping a record of the IDs of all existing and newly created assignments
	# note: indices of slice_map and observations_map are the same since they're constructed at the same time
	# during monitoring
	#slice_map = verdict_dictionary["verdict"][3]
	observations_map = verdict_dictionary["verdict"][2]
	path_map = verdict_dictionary["verdict"][3]
	path_condition_ids = []

	# find longest path length and just perform insertion for this path
	# all the others will be subpaths
	longest_path_index = verdict_dictionary["verdict"][3].keys()[0]
	for atom_index in path_map:
		if len(verdict_dictionary["verdict"][3][atom_index]) > len(verdict_dictionary["verdict"][3][longest_path_index]):
			longest_path_index = atom_index

	print("atom index %s has longest path" % longest_path_index)

	condition_id_sequence = verdict_dictionary["verdict"][3][longest_path_index]
	# insert empty condition at the beginning - we need to check if the empty condition exists in the database
	result = cursor.execute("select id from path_condition_structure where serialised_condition = ''").fetchall()
	if len(result) > 0:
		# the empty condition exists
		empty_condition_id = int(result[0][0])
	else:
		# we have to insert the empty condition
		cursor.execute("insert into path_condition_structure (serialised_condition) values('')")
		empty_condition_id = int(cursor.lastrowid)
	condition_id_sequence = [empty_condition_id] + condition_id_sequence

	print("performing insertion with condition id sequence %s" % str(condition_id_sequence))

	# before constructing the path based on the atom with the longest path sequence,
	# we trace forwards through condition_id_sequence to see if part of the path has already been inserted
	# by a previous verdict insertion from the same function call.
	# eventually we should change the way verdicts are sent from the service-level to send everything at once
	# and then path insertion will be simpler
	for (n, condition_id) in enumerate(condition_id_sequence):
		print("path check - %i with condition id %i and function call id %i" % (n, condition_id, new_function_call_id))
		result = cursor.execute("select id, next_path_condition from path_condition where serialised_condition = ? and function_call = ?", [condition_id, new_function_call_id]).fetchall()
		if len(result) == 0:
			# the only way this can happen is if there is no existing path - if the first path condition
			# in the chain exists, all others in the chain exist by construction.
			# we tell the path insertion that happens below where to start inserting the path from
			# in this case, the entire path must be inserted because nothing exists yet.

			print("no path found - inserting one")

			most_recent_id = None
			for (m, condition_id) in enumerate(condition_id_sequence[::-1]):
				# insert a new path_condition row for this condition_id
				next_path_condition = -1 if m == 0 else most_recent_id
				cursor.execute("insert into path_condition (serialised_condition, next_path_condition, function_call) values(?, ?, ?)",
					[condition_id, next_path_condition, new_function_call_id])
				print("inserted", condition_id, next_path_condition, new_function_call_id)
				most_recent_id = cursor.lastrowid
				path_condition_ids.append(most_recent_id)

			# reverse the id sequence since it's currently backwards due
			# due to inserting in reverse order
			path_condition_ids = path_condition_ids[::-1]

			break

		else:
			next_path_condition = result[0][1]
			path_condition_ids.append(result[0][0])
			if next_path_condition == -1 and n < len(condition_id_sequence)-1:
				# we've reached the end of the path condition chain, but we have more conditions to insert
				# from the verdict sent from the service-level.
				# this means we must extend the existing path
				# we do this by inserting the rest of the path (the remainder of condition_id_sequence)
				# and then updating the old end of path to point to the new extension

				print("existing path ended too soon - extending it...")
				print("starting by inserting extension from position %i" % (n+1))

				# insert the extension
				most_recent_id = None
				extension_condition_ids = []
				for (m, condition_id) in enumerate(condition_id_sequence[n+1:][::-1]):
					# insert a new path_condition row for this condition_id
					next_path_condition = -1 if m == 0 else most_recent_id
					cursor.execute("insert into path_condition (serialised_condition, next_path_condition, function_call) values(?, ?, ?)",
						[condition_id, next_path_condition, new_function_call_id])
					print("inserted", condition_id, next_path_condition, new_function_call_id)
					most_recent_id = cursor.lastrowid
					extension_condition_ids.append(most_recent_id)

				# reverse the list of condition ids of the path extension
				extension_condition_ids = extension_condition_ids[::-1]
				# add to the existing list of condition ids
				path_condition_ids += extension_condition_ids

				# update the old path
				cursor.execute("update path_condition set next_path_condition = ? where id = ?", [most_recent_id, result[0][0]])

				break
	
	print("path condition ids are %s" % path_condition_ids)

	# create the verdict
	# we don't check for an existing verdict - there won't be repetitions here
	# we have to create this before inserting slice data because slices map to observations, which map to verdicts
	verdict = verdict_dictionary["verdict"][0]
	verdict_time_obtained = verdict_dictionary["verdict"][1]
	collapsing_atom_index = verdict_dictionary["verdict"][4]
	cursor.execute("insert into verdict (binding, verdict, time_obtained, function_call, collapsing_atom) values (?, ?, ?, ?, ?)",
		[new_binding_id, verdict, verdict_time_obtained, new_function_call_id, collapsing_atom_index])
	new_verdict_id = cursor.lastrowid

	for atom_index in observations_map:
		# for now, without transition input data, we just insert observations
		# insert observation for this atom_index
		print(observations_map[atom_index])
		last_condition = path_condition_ids[len(path_map[atom_index])]
		cursor.execute("insert into observation (instrumentation_point, verdict, observed_value, previous_condition, atom_index) values(?, ?, ?, ?, ?)",
			[observations_map[atom_index][1], new_verdict_id, str(observations_map[atom_index][0]), last_condition, atom_index])
		observation_id = cursor.lastrowid

	connection.commit()

	connection.close()

def insert_property(property_dictionary):
	"""
	Given a dictionary describing a property (hash + serialised structure), insert into the database.
	"""

	connection = get_connection()
	cursor = connection.cursor()

	try:
		serialised_structure = {
			"bind_variables" : property_dictionary["serialised_bind_variables"],
			"property" : property_dictionary["serialised_formula_structure"]
		}
		serialised_structure = json.dumps(serialised_structure)
		cursor.execute("insert into property (hash, serialised_structure) values (?, ?)", [property_dictionary["formula_hash"], serialised_structure])
	except:
		# for now, the error was probably because of dupicate properties if instrumentation was run again.
		# instrumentation should only ever be run for new versions of code, so at some point
		# we will need to integrate version distinction into the schema.

		print("ERROR OCCURRED DURING INSERTION:")

		traceback.print_exc()

	try:
		atom_index_to_db_index = []
		
		# insert the atoms
		serialised_atom_list = property_dictionary["serialised_atom_list"]
		for pair in serialised_atom_list:
			cursor.execute("insert into atom (property_hash, serialised_structure, index_in_atoms) values (?, ?, ?)",
				[property_dictionary["formula_hash"], pair[1], pair[0]])
			atom_index_to_db_index.append(cursor.lastrowid)

		print(atom_index_to_db_index)

		# insert the function
		cursor.execute("insert into function (fully_qualified_name, property) values (?, ?)", [property_dictionary["function"], property_dictionary["formula_hash"]])
		connection.commit()
		connection.close()
		print("property and function inserted")
		return atom_index_to_db_index, cursor.lastrowid
	except:
		# for now, the error was probably because of dupicate properties if instrumentation was run again.
		# instrumentation should only ever be run for new versions of code, so at some point
		# we will need to integrate version distinction into the schema.

		print("ERROR OCCURRED DURING INSERTION:")

		traceback.print_exc()
		return "failure"


def insert_binding(binding_dictionary):
	"""
	Given a dictionary describing a binding (binding space index, function, lines), insert into the database.
	"""

	connection = get_connection()
	cursor = connection.cursor()

	try:
		print(binding_dictionary)
		cursor.execute("insert into binding (binding_space_index, function, binding_statement_lines) values (?, ?, ?)",
			[binding_dictionary["binding_space_index"], binding_dictionary["function"], json.dumps(binding_dictionary["binding_statement_lines"])])
		new_id = cursor.lastrowid
		connection.commit()
		connection.close()
		return new_id
	except:
		# for now, the error was probably because of dupicate properties if instrumentation was run again.
		# instrumentation should only ever be run for new versions of code, so at some point
		# we will need to integrate version distinction into the schema.

		print("ERROR OCCURRED DURING INSERTION:")

		traceback.print_exc()

		return "failure"


def insert_instrumentation_point(dictionary):
	"""
	Given a dictionary describing an instrumentation point, insert the instrumentation point,
	the atom-instrumentation point and binding-instrumentation point pairs.
	"""

	connection = get_connection()
	cursor = connection.cursor()

	try:
		print(dictionary)
		# TODO: add existence checks
		# insert instrumentation point
		cursor.execute("insert into instrumentation_point (serialised_condition_sequence, reaching_path_length) values (?, ?)",
			[json.dumps(dictionary["serialised_condition_sequence"]), dictionary["reaching_path_length"]])
		new_id = cursor.lastrowid
		
		# insert the atom-instrumentation point link
		cursor.execute("insert into atom_instrumentation_point_pair (atom, instrumentation_point) values (?, ?)", [dictionary["atom"], new_id])

		# insert the binding-instrumentation point link
		cursor.execute("insert into binding_instrumentation_point_pair (binding, instrumentation_point) values (?, ?)", [dictionary["binding"], new_id])

		connection.commit()
		connection.close()
		return new_id
	except:
		# for now, the error was probably because of dupicate properties if instrumentation was run again.
		# instrumentation should only ever be run for new versions of code, so at some point
		# we will need to integrate version distinction into the schema.

		print("ERROR OCCURRED DURING INSERTION:")

		traceback.print_exc()

		return "failure"

def insert_branching_condition(dictionary):
	"""
	Given a dictionary describing a branching condition, perform the insertion.
	"""
	connection = get_connection()
	cursor = connection.cursor()
	try:
		print(dictionary)
		# check for existence
		result = cursor.execute("select * from path_condition_structure where serialised_condition = ?", [dictionary["serialised_condition"]]).fetchall()
		if len(result) > 0:
			# condition already exists - return the existing ID
			return result[0][0]
		else:
			# condition is new - insert it
			cursor.execute("insert into path_condition_structure (serialised_condition) values (?)", [dictionary["serialised_condition"]])
			new_id = cursor.lastrowid
			connection.commit()
			connection.close()
			return new_id
	except:
		print("ERROR OCCURED DURING INSERTION:")
		traceback.print_exc()
		return "failure"

def list_verdicts(function_name):
	"""
	Given a function name, for each http request, for each function call, list the verdicts.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	function_id = cursor.execute("select id from function where fully_qualified_name = ?", [function_name]).fetchall()[0][0]

	bindings = cursor.execute("select * from binding where function = ?", [function_id]).fetchall()

	http_requests = cursor.execute("select * from http_request").fetchall()
	request_to_verdicts = {}
	for result in http_requests:
		request_to_verdicts[result[1]] = {}
		# find the function calls of function_name for this http request
		calls = cursor.execute("select * from function_call where http_request = ?", [result[0]]).fetchall()
		for call in calls:
			request_to_verdicts[result[1]][call[2]] = {}
			for binding in bindings:
				verdicts = cursor.execute("select * from verdict where binding = ? and function_call = ?", [binding[0], call[0]]).fetchall()
				request_to_verdicts[result[1]][call[2]][binding[0]] = verdicts
				truth_map = {1 : True, 0 : False}
				request_to_verdicts[result[1]][call[2]][binding[0]] = map(list, request_to_verdicts[result[1]][call[2]][binding[0]])
				for n in range(len(request_to_verdicts[result[1]][call[2]][binding[0]])):
					request_to_verdicts[result[1]][call[2]][binding[0]][n][1] = truth_map[request_to_verdicts[result[1]][call[2]][binding[0]][n][1]]

	connection.close()

	return request_to_verdicts

def list_http_requests(function_id):
	"""
	Return a list of all http requests - we may eventually want do to this with a time interval bound.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	http_requests = cursor.execute("select * from http_request").fetchall()

	# list only the requests for which there is a call to the function with function_id
	final_requests = []
	for request in http_requests:
		calls_with_function_id = cursor.execute("select * from function_call where function = ? and http_request = ?", [function_id, request[0]]).fetchall()
		if len(calls_with_function_id) > 0:
			final_requests.append(request)

	connection.close()

	return final_requests

def list_calls_during_request(http_request_id, function_name):
	"""
	Given an http request id, list the function calls of the given function during that request.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	function_calls = cursor.execute("select * from function_call where http_request = ? and function = ?", [http_request_id, function_name]).fetchall()

	connection.close()

	return function_calls

def list_verdicts_from_function_call(function_call_id):
	"""
	Given a function call id, return all the verdicts reached during this function call.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	verdicts = cursor.execute("select binding.binding_statement_lines, verdict.verdict, verdict.time_obtained from "+\
		"(verdict inner join binding on verdict.binding=binding.id) where verdict.function_call = ?", [function_call_id]).fetchall()

	connection.close()

	return verdicts

def list_functions():
	"""
	Return a list of all functions found.
	"""

	connection = get_connection()
	cursor = connection.cursor()

	functions = cursor.execute("select function.id, function.fully_qualified_name, function.property, property.serialised_structure from "+\
		"(function inner join property on function.property=property.hash)").fetchall()

	# process the functions into a hierarchy by splitting the function names up by dots
	dictionary_tree_structure = {}
	for function in functions:
		path = function[1].split(".")
		if not(dictionary_tree_structure.get(path[0])):
			dictionary_tree_structure[path[0]] = {}
		current_hierarchy_step = dictionary_tree_structure[path[0]]
		# iterate through the rest of the path
		for item in path[1:-1]:
			if not(current_hierarchy_step.get(item)):
				current_hierarchy_step[item] = {}
			current_hierarchy_step = current_hierarchy_step[item]

		if current_hierarchy_step.get(path[-1]):
			current_hierarchy_step[path[-1]].append(function)
		else:
			current_hierarchy_step[path[-1]] = [function]

	#print(dictionary_tree_structure)

	connection.close()

	return dictionary_tree_structure

def get_http_request_function_call_pairs(verdict, path):
	"""
	For the given verdict and path pair, find all the function calls inside that path that
	result in a verdict matching the one given.

	To do this, we first find all the functions that match the path given.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	path = "%s%%" % path

	truth_map = {"violating" : 0, "not-violating" : 1}

	final_map = {}

	# note that a function is unique wrt a property - so each row returned here is coupled with a single property
	functions = cursor.execute("select * from function where fully_qualified_name like ?", [path]).fetchall()

	# Now, get all the calls to these functions and, for each call, find all the verdicts and organise them by binding

	final_map["functions"] = {}
	for function in functions:
		final_map["functions"][function[0]] = {"calls" : {}, "property" : {}, "fully_qualified_name" : function[1]}
		data_found_for_function = False

		# get the property string representation
		property_id = function[2]
		property_info = json.loads(cursor.execute("select * from property where hash = ?", [property_id]).fetchall()[0][1])
		final_map["functions"][function[0]]["property"] = property_info

		# get the calls
		calls = cursor.execute("select * from function_call where function = ?", [function[0]]).fetchall()
		for call in calls:
			data_found_for_call = False
			final_map["functions"][function[0]]["calls"][call[0]] = {"bindings" : {}, "time" : call[2]}
			bindings = cursor.execute("select * from binding where function = ?", [function[0]]).fetchall()
			for binding in bindings:
				verdicts = cursor.execute("select * from verdict where binding = ? and function_call = ? and verdict = ?", [binding[0], call[0], truth_map[verdict]]).fetchall()
				verdict_tuples = map(lambda row : (row[2], row[3]), verdicts)
				if len(verdict_tuples) > 0:
					final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]] = {"verdicts" : [], "lines" : binding[3]}
					final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]]["verdicts"] = verdict_tuples
					data_found_for_call = True
					data_found_for_function = True

			if not(data_found_for_call):
				del final_map["functions"][function[0]]["calls"][call[0]]

		if not(data_found_for_function):
			del final_map["functions"][function[0]]

	return final_map




def list_functions2():
	connection = get_connection()
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()
	
	list1 = cursor.execute("select * from function;")
	functions=list1.fetchall()
	connection.close()
	return json.dumps( [dict(f) for f in functions] )


def list_calls_function(function_name):
	connection = get_connection()
	cursor = connection.cursor()
	
	connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
	
	list1 = cursor.execute("select * from (function inner join function_call on function.id=function_call.function) where function.fully_qualified_name like ?",[function_name])
	functions=list1.fetchall()
	connection.close()
	return json.dumps([dict(f) for f in functions])

"""
Path reconstruction functions.
"""

def construct_new_search_tree(connection, cursor, root_observation, observation_list, instrumentation_point_id):
	"""
	Given a list of observations and an instrumentation point id, construct a new search tree.
	"""

	# create a new root vertex
	cursor.execute("insert into search_tree_vertex (observation, start_of_path, parent_vertex) values(?, -1, -1)", [root_observation])
	search_tree_vertex_root_id = cursor.lastrowid
	# insert the rest of the observations
	insert_observations_from_vertex(connection, cursor, observation_list, search_tree_vertex_root_id)
	# create a new search tree, and insert a path for the current set
	cursor.execute("insert into search_tree (root_vertex, instrumentation_point) values(?, ?)", [search_tree_vertex_root_id, instrumentation_point_id])
	new_search_tree_id = cursor.lastrowid
	connection.commit()

	return new_search_tree_id

def insert_observations_from_vertex(connection, cursor, observations, vertex_id):
	"""
	Given a list of observations and a vertex id in search tree, add the new path starting from that vertex.
	"""
	print("inserting new path for observation sequence %s from vertex %i" % (str(observations), vertex_id))
	parent_vertex_id = vertex_id
	for obs in observations:
		cursor.execute("insert into search_tree_vertex (observation, start_of_path, parent_vertex) values(?, -1, ?)", [obs, parent_vertex_id])
		parent_vertex_id = cursor.lastrowid
	connection.commit()

def get_qualifier_subsequence(function_qualifier):
	"""
	Given a fully qualified function name, iterate over it and find the file
	in which the function is defined (this is the entry in the qualifier chain
	before the one that causes an import error)/
	"""

	# tokenise the qualifier string so we have names and symbols
	# the symbol used to separate two names tells us what the relationship is
	# a/b means a is a directory and b is contained within it
	# a.b means b is a member of a, so a is either a module or a class

	tokens = []
	last_position = 0
	for (n, character) in enumerate(list(function_qualifier)):
		if character in [".", "/"]:
			tokens.append(function_qualifier[last_position:n])
			tokens.append(function_qualifier[n])
			last_position = n + 1
		elif n == len(function_qualifier)-1:
			tokens.append(function_qualifier[last_position:])

	return tokens

def construct_function_scfg(function):
	"""
	Given a function name, find the function definition in the service code and construct the SCFG.
	"""

	module = function[0:function.rindex(".")]
	function = function[function.rindex(".")+1:]

	file_name = module.replace(".", "/") + ".py.inst"
	file_name_without_extension = module.replace(".", "/")

	# extract asts from the code in the file
	code = "".join(open(os.path.join("/servers/TestService/", file_name), "r").readlines())
	asts = ast.parse(code)

	print(asts.body)

	qualifier_subsequence = get_qualifier_subsequence(function)
	function_name = function.split(".")

	# find the function definition
	print("finding function/method definition using qualifier chain %s" % function_name)

	actual_function_name = function_name[-1]
	hierarchy = function_name[:-1]

	print(actual_function_name, hierarchy)

	current_step = asts.body

	# traverse sub structures

	for step in hierarchy:
		current_step = filter(
			lambda entry : (type(entry) is ast.ClassDef and
				entry.name == step),
			current_step
		)[0]

	# find the final function definition

	function_def = filter(
		lambda entry : (type(entry) is ast.FunctionDef and
			entry.name == actual_function_name),
		current_step.body if type(current_step) is ast.ClassDef else current_step
	)[0]

	# construct the scfg of the code inside the function
	scfg = CFG()
	scfg_vertices = scfg.process_block(function_def.body)

	return scfg

def reconstruct_path(cursor, scfg, observation_id):
	"""
	Given an observation, determine the function that generated it,
	construct that function's SCFG, then reconstruct the path taken by the observation
	through this SCFG.
	"""

	observation = cursor.execute(
"""
select function.fully_qualified_name, verdict.function_call,
		observation.instrumentation_point, observation.previous_condition,
		observation.observed_value
from
(((observation inner join verdict on observation.verdict == verdict.id)
	inner join binding on verdict.binding == binding.id)
		inner join function on binding.function == function.id)
where observation.id == ?
""", [observation_id]).fetchall()[0]

	function_name = observation[0]
	function_call_id = observation[1]
	instrumentation_point_id = observation[2]
	previous_path_condition_entry = observation[3]
	observed_value = observation[4]

	# reconstruct the path up to the observation through the SCFG
	# get the starting path condition in the path condition sequence for function_call_id
	path_conditions = cursor.execute("select * from path_condition where function_call = ?", [function_call_id]).fetchall()
	for path_condition in path_conditions:
		# check if there are any other path conditions that refer to this one
		# if there are none, we have the first one
		check = cursor.execute("select * from path_condition where function_call = ? and next_path_condition = ?", [function_call_id, path_condition[0]]).fetchall()
		if len(check) == 0:
			print(path_condition)
			first_path_condition_id = path_condition[0]
			break
	print("first path condition for this call is %i" % first_path_condition_id)
	print("reconstructing chain")
	current_path_condition_id = first_path_condition_id
	path_chain = []
	path_id_chain = []
	while current_path_condition_id != -1:
		path_id_chain.append(current_path_condition_id)
		current_path_condition = cursor.execute("select * from path_condition where id = ?", [current_path_condition_id]).fetchall()[0]
		current_path_condition_id = current_path_condition[-2]
		serialised_condition_id = current_path_condition[1]
		serialised_condition = cursor.execute("select * from path_condition_structure where id = ?", [serialised_condition_id]).fetchall()[0][1]
		if serialised_condition != "":
			if not(serialised_condition in ["conditional exited", "try-catch exited", "try-catch-main"]):
				unserialised_condition = pickle.loads(serialised_condition)
			else:
				unserialised_condition = serialised_condition
		else:
			unserialised_condition = None
		path_chain.append(unserialised_condition)

	print(path_id_chain)
	print(path_chain)

	# remove the first condition, since it's None
	path_chain = path_chain[1:]

	instrumentation_point_path_length = int(cursor.execute("select reaching_path_length from instrumentation_point where id = ?", [instrumentation_point_id]).fetchall()[0][0])

	print("reconstructing path for observation %s with previous condition %i and value %s based on chain %s" %\
		(observation_id, previous_path_condition_entry, str(observed_value), path_chain))

	# traverse the SCFG based on the derived condition chain
	path_subchain = path_chain[0:path_id_chain.index(previous_path_condition_entry)]
	print("traversing using condition subchain %s" % path_subchain)
	condition_index = 0
	curr = scfg.starting_vertices
	#path = [curr]
	path = []
	cumulative_conditions = []
	while condition_index < len(path_subchain):
		#path.append(curr)
		#print(curr._name_changed)
		if len(curr.edges) > 1:
			# more than 1 outgoing edges means we have a branching point
			# we have to decide whether it's a loop or a conditional
			if curr._name_changed == ["conditional"]:
				print("traversing conditional %s with condition %s" % (curr, path_subchain[condition_index]))
				# search the outgoing edges for an edge whose condition has the same length as path_chain[condition_index]
				for edge in curr.edges:
					print("testing edge condition %s against condition %s" %\
						(edge._condition[-1], path_chain[condition_index][0]))
					# for now we assume that conditions are single objects (ie, not conjunctions)
					if type(edge._condition[-1]) == type(path_chain[condition_index][0]):
						# conditions match
						print("traversing edge with condition %s" % edge._condition[-1])
						curr = edge._target_state
						path.append(edge)
						cumulative_conditions.append(edge._condition[-1])
						break
				# make sure the next branching point consumes the next condition in the chain
				condition_index += 1
			elif curr._name_changed == ["loop"]:
				print("traversing loop %s with condition %s" % (curr, path_subchain[condition_index]))
				if not(type(path_subchain[condition_index]) is LogicalNot):
					# condition isn't a negation, so follow the edge leading into the loop
					for edge in curr.edges:
						if not(type(edge._condition) is LogicalNot):
							print("traversing edge with positive loop condition")
							cumulative_conditions.append("for")
							# follow this edge
							curr = edge._target_state
							path.append(edge)
							break
					# make sure the next branching point consumes the next condition in the chain
					condition_index += 1
				else:
					# go straight past the loop
					for edge in curr.edges:
						if type(edge._condition) is LogicalNot:
							print("traversing edge with negative loop condition")
							cumulative_conditions.append(edge._condition)
							# follow this edge
							curr = edge._target_state
							path.append(edge)
							break
					# make sure the next branching point consumes the next condition in the chain
					condition_index += 1
			elif curr._name_changed == ["try-catch"]:
				print("traversing try-catch")
				# for now assume that we immediately traverse the no-exception branch
				print(curr)
				# search the outgoing edges for the edge leading to the main body
				for edge in curr.edges:
					print("testing edge with condition %s against cumulative condition %s" %\
							(edge._condition, cumulative_conditions + [path_chain[condition_index]]))
					if edge._condition[-1] == "try-catch-main":
						print("traversing edge with condition %s" % edge._condition)
						curr = edge._target_state
						path.append(edge)
						cumulative_conditions.append(edge._condition[-1])
						break
				condition_index += 1
			else:
				# probably the branching point at the end of a loop - currently these aren't explicitly marked
				# the behaviour here with respect to consuming branching conditions will be a bit different
				if not(type(path_subchain[condition_index]) is LogicalNot):
					# go back to the start of the loop without consuming the condition
					print("going back around the loop")
					relevant_edge = filter(lambda edge : edge._condition == 'loop-jump', curr.edges)[0]
					curr = relevant_edge._target_state
					path.append(relevant_edge)
				else:
					# go past the loop
					print(curr.edges)
					print("ending loop")
					relevant_edge = filter(lambda edge : edge._condition == 'post-loop', curr.edges)[0]
					curr = relevant_edge._target_state
					path.append(relevant_edge)
					# consume the negative condition
					condition_index += 1

			print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
		elif curr._name_changed == ["post-conditional"]:
			print("traversing post-conditional")
			# check the next vertex - if it's also a post-conditional, we move to that one but don't consume the condition
			# if the next vertex isn't a post-conditional, we consume the condition and move to it
			if curr.edges[0]._target_state._name_changed != ["post-conditional"]:
				# consume the condition
				condition_index += 1
			path.append(curr.edges[0])
			curr = curr.edges[0]._target_state
			print("resulting state after conditional is %s" % curr)
			print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
		elif curr._name_changed == ["post-loop"]:
			print("traversing post-loop")
			# condition is consumed when branching at the end of the loop is detected, so no need to do it here
			print("adding %s outgoing from %s to path" % (curr.edges[0], curr))
			path.append(curr.edges[0])
			curr = curr.edges[0]._target_state
			print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
		elif curr._name_changed == ["post-try-catch"]:
			print("traversing post-try-catch")
			if curr.edges[0]._target_state._name_changed != ["post-try-catch"]:
				# consume the condition
				condition_index += 1
			path.append(curr.edges[0])
			curr = curr.edges[0]._target_state
			print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
		else:
			print("no branching at %s" % curr)
			path.append(curr.edges[0])
			curr = curr.edges[0]._target_state
			print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))

	print("finishing path traversal with path length %i" % instrumentation_point_path_length)

	# traverse the remainder of the branch using the path length of the instrumentation point
	# that generated the observation we're looking at
	print("starting remainder of traversal from vertex %s" % curr)
	limit = instrumentation_point_path_length-1 if len(path_subchain) > 0 else instrumentation_point_path_length
	for i in range(limit):
		#path.append(curr)
		path.append(curr.edges[0])
		curr = curr.edges[0]._target_state

	#path.append(curr)

	print("reconstructed path is %s" % path)

	return path


def reconstruct_paths(cursor, scfg, observation_ids):
	"""
	Given a sequence of observations
	"""
	return map(lambda observation_id : reconstruct_path(cursor, scfg, observation_id), observation_ids)

def compute_intersection(s, instrumentation_point_id):
	"""
	Given a list s of observations and an instrumentation point ID, compute the intersection
	of the reconstructed paths using existing results as much as possible.
	"""
	connection = get_connection()
	cursor = connection.cursor()

	# get the name of the function from which the observation came
	# the route taken through the verdict schema here is the shortest one I can think of
	function_name = cursor.execute(
"""
select function.fully_qualified_name from
(((observation inner join verdict on observation.verdict == verdict.id)
	inner join binding on verdict.binding == binding.id)
		inner join function on binding.function == function.id)
where observation.id == ?
""", [s[0]]).fetchall()[0][0]

	# construct the scfg of the function from which the observation came
	scfg = construct_function_scfg(function_name)

	# derive a rule system from the scfg
	grammar_rules_map = scfg.derive_grammar()

	# get all existing search trees for the instrumentation point ID we have
	search_trees = cursor.execute("select * from search_tree where instrumentation_point = ?", [instrumentation_point_id]).fetchall()

	if len(search_trees) > 0:

		print("processing search trees for observation sequence %s" % str(s))

		# attempt to get the search tree with a root matching one of the elements of this list
		root_observation_id = None
		for obs in s:
			# find the search tree with a root matching an observation from this set
			for tree in search_trees:
				root_vertex = cursor.execute("select * from search_tree_vertex where id = ?", [tree[1]]).fetchall()[0]
				if root_vertex[1] == obs:
					# the root matches this observation, so we can use this search tree
					root_observation_id = obs
					root_vertex_id = tree[1]
					# break out of the loop - we've found the search tree we can use
					break

		# check if we found a search tree we can use for this set of observations
		if not(root_observation_id):
			# there were search trees for this instrumentation point, but none had a root we could use
			# so now we construct a new search tree whose root is s[0]
			print("no suitable search tree found - constructing a new one")
			construct_new_search_tree(connection, cursor, s[0], s[1:], instrumentation_point_id)

		else:
			print("suitable search tree found - attempting traversal")
			# if we found a search tree, traverse it and see if the intersection for this set of observations
			# has already been computed
			# root already exists, so remove it
			s.remove(root_observation_id)
			# here, we iterate until there are no observations remaining
			# each iteration, we go through the remaining observations and see if we can traverse the tree further
			parent_vertex_id = root_vertex_id
			while len(s) > 0:

				print("remaining observations %s" % str(s))

				# search for a next vertex that we can follow
				next_vertex = None

				for obs in s:
					print("looking for vertices with observation %i and parent %i" % (obs, parent_vertex_id))
					next_vertex_list = cursor.execute("select * from search_tree_vertex where observation = ? and parent_vertex = ?", [obs, parent_vertex_id]).fetchall()
					if len(next_vertex_list) > 0:
						next_vertex = next_vertex_list[0]
						break

				# if we found a vertex, we can progress, otherwise we have to insert new vertices
				if next_vertex:
					print("can progress!")
					# remove the observation
					s.remove(obs)
					# move to the next vertex
					parent_vertex_id = next_vertex[0]
				else:
					# there's no vertex we can follow with the observations we have
					# the only way to continue is to extend the tree
					# we choose the first element from the remaining set
					print("can't progress! doing insertion for observation id %i with parent vertex %i" % (s[0], parent_vertex_id))
					# add the new path
					cursor.execute("insert into search_tree_vertex (observation, start_of_path, parent_vertex) values(?, -1, ?)", [s[0], parent_vertex_id])
					starting_vertex = cursor.lastrowid
					# remove the observation we've just used
					s.remove(s[0])
					print("adding a new path for remaining observations %s" % str(s))
					insert_observations_from_vertex(connection, cursor, s, starting_vertex)
					break


	else:
		# no search tree was found for this instrumentation point
		print("no search tree found for observation sequence %s - constructing a new one" % str(s))
		new_tree_id = construct_new_search_tree(connection, cursor, s[0], s[1:], instrumentation_point_id)

		# if we didn't find a search tree, then the intersection isn't computed yet (since we check
		# for search trees whose roots are any element in the list of observations we have).

		paths = reconstruct_paths(cursor, scfg, s)

		parse_trees = []
		for (path_index, path) in enumerate(paths):
			print("="*100)
			print("constructing parse tree for path")
			print(path)

			parse_tree = ParseTree(path, grammar_rules_map, scfg.starting_vertices)

			parse_trees.append(parse_tree)
			generated_path = parse_tree._path_progress

			print("path generated by parse tree:")
			print(generated_path)

	# parse_trees will be defined by the end of the previous conditional block
	intersection = parse_trees[0].intersect(parse_trees[1:])
	parametric_path = []
	# will populate parametric_path with the path read off the intersection parse tree
	intersection.leaves_to_left_right_sequence(intersection._root_vertex, parametric_path)
	return str(parametric_path)