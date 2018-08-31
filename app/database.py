"""
Module to handle interaction with the verdict database.
"""

# use sqlite for now
import sqlite3
import traceback
import json

database_string = "verdicts.db"

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
	if len(results) == 0:
		# the function hasn't already been encountered, so insert it
		cursor.execute("insert into function (fully_qualified_name, property) values (?, ?)", [verdict_dictionary["function_name"], verdict_dictionary["property_hash"]])
		connection.commit()
		# get the id
		new_function_id = int(cursor.execute("select id from function where fully_qualified_name = ? and property = ?", [verdict_dictionary["function_name"], verdict_dictionary["property_hash"]]).fetchall()[0][0])
	else:
		# get the id of the existing function
		new_function_id = int(results[0][0])

	# create the binding if it doesn't already exist
	results = cursor.execute("select * from binding where binding_space_index = ? and function = ?", [verdict_dictionary["bind_space_index"], new_function_id]).fetchall()
	if len(results) == 0:
		# no binding exists yet, so insert a new binding
		cursor.execute("insert into binding (binding_space_index, function, binding_statement_lines) values (?, ?, ?)",
			[verdict_dictionary["bind_space_index"], new_function_id, verdict_dictionary["line_numbers"]])
		connection.commit()
		# get the id
		new_binding_id = int(cursor.execute("select id from binding where binding_space_index = ? and function = ?", [verdict_dictionary["bind_space_index"], new_function_id]).fetchall()[0][0])
	else:
		# get the id of the existing binding
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
		# get the id of the existing binding
		new_http_request_id = int(results[0][0])

	# insert the function call that the verdict belongs to
	results = cursor.execute("select * from function_call where time_of_call = ? and function = ?", [verdict_dictionary["time_of_call"], new_function_id]).fetchall()
	if len(results) == 0:
		# no binding exists yet, so insert a new binding
		cursor.execute("insert into function_call (function, time_of_call, http_request) values (?, ?, ?)",
			(new_function_id, verdict_dictionary["time_of_call"], new_http_request_id))
		connection.commit()
		# get the id
		new_function_call_id = int(cursor.execute("select id from function_call where time_of_call = ? and function = ?", [verdict_dictionary["time_of_call"], new_function_id]).fetchall()[0][0])
	else:
		# get the id of the existing binding
		new_function_call_id = int(results[0][0])

	# create the verdict
	# we don't check for an existing verdict - there won't be repetitions here
	verdict = verdict_dictionary["verdict"][0]
	verdict_time_obtained = verdict_dictionary["verdict"][1]
	cursor.execute("insert into verdict (binding, verdict, time_obtained, function_call) values (?, ?, ?, ?)",
		[new_binding_id, verdict, verdict_time_obtained, new_function_call_id])
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
		connection.commit()
		connection.close()
	except:
		# for now, the error was probably because of dupicate properties if instrumentation was run again.
		# instrumentation should only ever be run for new versions of code, so at some point
		# we will need to integrate version distinction into the schema.

		print("ERROR OCCURRED DURING INSERTION:")

		traceback.print_exc()

		return False

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

		# get the property string representation
		property_id = function[2]
		property_info = json.loads(cursor.execute("select * from property where hash = ?", [property_id]).fetchall()[0][1])
		final_map["functions"][function[0]]["property"] = property_info

		# get the calls
		calls = cursor.execute("select * from function_call where function = ?", [function[0]]).fetchall()
		for call in calls:
			final_map["functions"][function[0]]["calls"][call[0]] = {"bindings" : {}, "time" : call[2]}
			bindings = cursor.execute("select * from binding where function = ?", [function[0]]).fetchall()
			for binding in bindings:
				final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]] = {"verdicts" : [], "lines" : binding[3]}
				verdicts = cursor.execute("select * from verdict where binding = ? and function_call = ? and verdict = ?", [binding[0], call[0], truth_map[verdict]]).fetchall()
				final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]]["verdicts"] = map(lambda row : (row[1], row[2]), verdicts)

	return final_map