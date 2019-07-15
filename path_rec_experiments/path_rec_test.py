from __future__ import print_function
def print(*args):
	pass
"""
Path reconstruction test module.
For each function in the verdict database given, find all observations from that function.
For each observation, reconstruct the execution path up to that point.
"""

import argparse
import sqlite3
import traceback
import sys
import os
import ast
import pickle
import pprint

sys.path.append("VyPR/")
# TO BE CHANGED BY ANYONE RUNNING THIS SCRIPT
BASE = "/servers/TestService/"
sys.path.append(BASE)

from control_flow_graph.construction import *
from monitor_synthesis.formula_tree import *
from control_flow_graph.parse_tree import *

def print_break():
	print("="*100)

def write_scfg_with_path_to_file(scfg, file_name, path):
	"""
	Given an scfg and a file name, write the scfg in dot format to the file.
	The list of edges given in path will be highlighted (as the target vertex of each edge)
	"""
	graph = Digraph()
	graph.attr("graph", splines="true", fontsize="10")
	shape = "rectangle"
	vertices_to_highlight = map(lambda edge : edge._target_state, path)
	for vertex in scfg.vertices:
		colour = "red" if vertex in vertices_to_highlight else "black"
		graph.node(str(id(vertex)), str(vertex._name_changed), shape=shape, color=colour)
		for edge in vertex.edges:
			"""graph.edge(
				str(id(vertex)),
				str(id(edge._target_state)),
				"%s : %s\n%s" % (str(edge._condition), str(edge._operates_on), str(edge._target_state._path_length))
			)"""
			graph.edge(
				str(id(vertex)),
				str(id(edge._target_state)),
				"%s - %s - path length = %s" %\
					(str(edge._operates_on) if not(type(edge._operates_on[0]) is ast.Print) else "print stmt",
					edge._condition,
					str(edge._target_state._path_length))
			)
	graph.render(file_name)
	print("Writing SCFG to file '%s'." % file_name)

def scfg_element_to_dot(scfg_obj):
	"""
	Gives a string that can be used by dot for drawing parse trees.
	"""
	return str(scfg_obj).replace("<", "").replace(">", "")

def write_parse_tree_to_file(parse_tree, file_name):
	"""
	Given a parse tree for a path wrt a scfg, write a dot file.
	"""
	graph = Digraph()
	graph.attr("graph", splines="true", fontsize="10")
	shape = "rectangle"
	for vertex in parse_tree._vertices:
		#print(str(vertex._symbol))
		colour = "black"
		graph.node(str(id(vertex)), scfg_element_to_dot(vertex._symbol), shape=shape, color=colour)
		for child in vertex._children:
			graph.edge(
				str(id(vertex)),
				str(id(child))
			)
	graph.render(file_name)
	print("Written parse tree to file '%s'." % file_name)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='For each function in the verdict database file given by --db, find the observations and reconstruct their execution paths.')
	parser.add_argument('--db', type=str, required=True, help="Path to the SQLite verdict database file to take verdict data from.")

	args = parser.parse_args()
	con = sqlite3.connect(args.db)
	cursor = con.cursor()

	function_id_pairs = map(lambda row : (row[0], row[1].split(".")), cursor.execute("select * from function").fetchall())


	for (function_id, name_chain) in function_id_pairs:

		# check for actual calls of this function before we do all the processing
		calls = cursor.execute("select * from function_call where function = ?", [function_id]).fetchall()
		if len(calls) == 0:
			# if there are no calls of this function, skip it
			continue

		# get the function's body

		file_qualifier = name_chain[:-1]
		file_name_string = "%s.py.inst" % ("/".join(file_qualifier))
		function_qualifier = name_chain[-1].split(":")

		print("Looking in file %s for function with chain %s" % (file_name_string, function_qualifier))
		print_break()

		# attempt to open the file
		with open(os.path.join(BASE, file_name_string), "r") as h:
			code = h.read()
			asts = ast.parse(code)

		actual_function_name = function_qualifier[-1]
		print("Navigating hierarchy to find function %s" % actual_function_name)

		hierarchy = function_qualifier[:-1]

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

		# construct the scfg of the code inside the function - we need this for path reconstruction
		scfg = CFG()
		scfg_vertices = scfg.process_block(function_def.body)

		# derive a context free grammar from the scfg
		grammar_rules_map = scfg.derive_grammar()

		print("testing keys")
		for vertex in scfg.vertices:
			print(vertex, vertex in grammar_rules_map.keys())

		print("reconstructing paths")
		print("="*100)

		# get all observations for this function - via bindings, then verdicts, then observations
		binding_ids = map(lambda row : row[0], cursor.execute("select * from binding where function = ?", [function_id]).fetchall())
		print(binding_ids)
		for binding_id in binding_ids:
			# get the verdicts from this binding
			verdicts = cursor.execute("select * from verdict where binding = ?", [binding_id]).fetchall()
			print(verdicts)
			# for now, we just use the sign of the verdict...
			# we need to be able to do more detailed analysis
			good_paths = []
			bad_paths = []
			for verdict in verdicts:
				verdict_id = verdict[0]
				verdict_binding = verdict[1]
				function_call_id = verdict[-2]
				verdict_truth_value = verdict[2]
				print("processing observations for verdict from call to %s with id %i" % (function_qualifier, function_call_id))
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

				# temporary extra criteria on the instrumentation point
				observations = cursor.execute("select * from observation where verdict = ? and instrumentation_point = 2", [verdict_id]).fetchall()
				paths = []
				for observation in observations:
					print_break()
					observation_id = observation[0]
					instrumentation_point_id = observation[1]
					previous_path_condition_entry = observation[5]
					observed_value = observation[3]
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
									"""if len(edge._condition[-1]) == len(path_chain[condition_index][0]):
										# now make sure types match
										match = True
										for cond_pair in zip(edge._condition[-1], path_chain[condition_index][0]):
											if type(cond_pair[0]) != type(cond_pair[1]):
												match = False
												break
										if match:
											# conditions match
											print("traversing edge with condition %s" % edge._condition[-1])
											curr = edge._target_state
											path.append(edge)
											cumulative_conditions.append(edge._condition[-1])
											break"""
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

					# write the SCFG to a file with the path highlighted
					#write_scfg_with_path_to_file(scfg, "scfgs_with_paths/%s-obs-%i.gv" % ("-".join(name_chain).replace(":", "-"), observation_id), path)
					paths.append(path)

					# get the observations from this verdict
					observations = cursor.execute("select * from observation where verdict = ?", [verdict_id]).fetchall()
					for observation in observations:
						path_condition_id = observation[-1]
						print("observation found coming after the path condition id %i" % path_condition_id)

				print("paths reconstructed for verdict %s" % (verdict,))
				print("now, constructing parse trees wrt grammar")
				#pprint.pprint(grammar_rules_map)
				print("="*100)
				parse_trees = []
				if verdict_truth_value:
					good_paths += paths
				else:
					bad_paths += paths
				for (path_index, path) in enumerate(paths):
					print("="*100)
					print("constructing parse tree for path")
					print(path)

					print(scfg.starting_vertices in grammar_rules_map.keys())

					parse_tree = ParseTree(path, grammar_rules_map, scfg.starting_vertices)
					"""print("all paths through parse tree:")
					print(parse_tree._all_paths)"""

					parse_trees.append(parse_tree)
					generated_path = parse_tree._path_progress

					print("path generated by parse tree:")
					print(generated_path)

					#write_parse_tree_to_file(parse_tree, "parse-trees/%s-binding-%i-verdict-%i-path-%i.gv" % ("-".join(name_chain).replace(":", "-"), binding_id, verdict_id, path_index))

				#intersected_parse_tree = parse_trees[0].intersect(parse_trees[1])
				#write_parse_tree_to_file(intersected_parse_tree, "parse-trees/intersection.gv")

		# form the intersection
		paths = good_paths + bad_paths
		parse_trees = map(lambda path : ParseTree(path, grammar_rules_map, scfg.starting_vertices), paths)
		intersection = parse_trees[0].intersect(parse_trees[1:])
		#write_parse_tree_to_file(intersection, "parse-trees/intersection.gv")

		print("Intersection of all paths written to parse-trees/intersection.gv")

		flattened_path = []
		intersection.leaves_to_left_right_sequence(intersection._root_vertex, flattened_path)
		print("flattened_path is ")
		print(flattened_path)

		print("with parameters")
		#print(filter(lambda el : type(el) is CFGVertex, flattened_path))
		path_parameters = []
		intersection.get_parameter_paths(intersection._root_vertex, [], path_parameters)

		# use the parameter paths derived from the intersected path to determine the set of values
		# of the parameter given by paths in the intersection

		for path_parameter in path_parameters:
			values = map(lambda parse_tree : parse_tree.get_parameter_subtree(path_parameter), parse_trees)

			print("path parameter %s has values" % path_parameter)
			print(values)

			for (n, subtree) in enumerate(values):
				#write_parse_tree_to_file(subtree, "parse-trees/parameter-%i.gv" % n)

				subpath = map(lambda vertex : vertex._symbol, filter(lambda el : type(el._symbol) is CFGEdge, subtree._vertices))

				# write an scfg with this subpath highlighted
				#write_scfg_with_path_to_file(scfg, "scfgs_with_paths/subpath-parameter-%i.gv" % n, subpath)
		
		print("good paths are")
		print(good_paths)
		good_parse_trees = map(lambda path : ParseTree(path, grammar_rules_map, scfg.starting_vertices), good_paths)

		# form intersection of all the good paths to get a representative path
		good_representative = good_parse_trees[0].intersect(good_parse_trees[1:])
		#write_parse_tree_to_file(good_representative, "parse-trees/good-representative.gv")

		print("bad paths are")
		print(bad_paths)
		bad_parse_trees = map(lambda path : ParseTree(path, grammar_rules_map, scfg.starting_vertices), bad_paths)

		# form intersection of all the bad paths to get a representative path
		bad_representative = bad_parse_trees[0].intersect(bad_parse_trees[1:])
		#write_parse_tree_to_file(bad_representative, "parse-trees/bad-representative.gv")

		good_bad_intersection = good_representative.intersect([bad_representative])
		#write_parse_tree_to_file(good_bad_intersection, "parse-trees/good-bad-intersection.gv")

		flattened_path = []
		good_bad_intersection.leaves_to_left_right_sequence(good_bad_intersection._root_vertex, flattened_path)
		print("flattened_path is ")
		print(flattened_path)

		print("with parameters")
		print(filter(lambda el : type(el) is CFGVertex, flattened_path))

		#pprint.pprint(paths)
		#pprint.pprint(grammar_rules_map)
