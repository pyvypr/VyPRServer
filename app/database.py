"""
Module to handle interaction with the verdict database.
"""

import sqlite3
import traceback

from .paths import *

database_string = "verdicts.db"

from VyPR.SCFG.parse_tree import ParseTree


def get_connection():
    # for now, let exceptions appear in the log
    global database_string
    return sqlite3.connect(database_string)


def insert_function_call_data(call_data):
    """
    Given function call data, create the transaction, function call and program path.
    """
    connection = get_connection()
    cursor = connection.cursor()

    print(str(call_data))

    # insert transaction
    # since this data is received from the monitored service potentially
    # multiple times per transaction, we have to check whether a transaction
    # already exists in the database

    transactions = cursor.execute("select * from trans where time_of_transaction = ?",
                                  [call_data["transaction_time"]]).fetchall()
    if len(transactions) == 0:
        cursor.execute("insert into trans (time_of_transaction) values(?)",
                       [call_data["transaction_time"]])
        transaction_id = cursor.lastrowid
        connection.commit()
    else:
        transaction_id = transactions[0][0]

    print("transaction created")

    # insert call

    try:

        function_id = cursor.execute("select id from function where fully_qualified_name = ? and property = ?",
                                     (call_data["function_name"], call_data["property_hash"])).fetchall()[0][0]

    except Exception:
        traceback.print_exc()

    print("obtained function id")

    cursor.execute(
        "insert into function_call (function, time_of_call, end_time_of_call, trans) values(?, ?, ?, ?)",
        [function_id, call_data["time_of_call"], call_data["end_time_of_call"], transaction_id])
    function_call_id = cursor.lastrowid
    connection.commit()

    print("function call created")

    # insert program path

    program_path = call_data["program_path"]

    # check for the empty condition
    empty_condition = cursor.execute(
        "select * from path_condition_structure where serialised_condition = ''").fetchall()
    if len(empty_condition) == 0:
        cursor.execute("insert into path_condition_structure (serialised_condition) values('')")
        empty_condition_id = cursor.lastrowid
    else:
        empty_condition_id = empty_condition[0][0]

    new_program_path = [empty_condition_id] + program_path
    reversed_program_path = new_program_path[::-1]

    next_condition_id = -1

    for (n, condition_id) in enumerate(reversed_program_path):
        cursor.execute(
            "insert into path_condition (serialised_condition, next_path_condition, function_call) values(?, ?, ?)",
            [condition_id, next_condition_id, function_call_id])
        next_condition_id = cursor.lastrowid

    connection.commit()
    connection.close()

    print("program path created")

    return {"function_call_id": function_call_id, "function_id": function_id}


def insert_verdicts(verdict_dictionary):
    connection = get_connection()
    cursor = connection.cursor()

    print("Performing verdicts insertion")

    function_call_id = verdict_dictionary["function_call_id"]

    # get path condition IDs - they were inserted before any verdicts
    # we get the sequence in reverse and then reverse it
    current_in_path = cursor.execute(
        "select * from path_condition where next_path_condition = -1 and function_call = ?",
        [function_call_id]
    ).fetchall()[0]
    reversed_path_sequence = [current_in_path[0]]
    next_in_path = cursor.execute(
        "select * from path_condition where next_path_condition = ?",
        [current_in_path[0]]
    ).fetchall()
    while len(next_in_path) == 1:
        reversed_path_sequence.append(next_in_path[0][0])
        next_in_path = cursor.execute(
            "select * from path_condition where next_path_condition = ?",
            [next_in_path[0][0]]
        ).fetchall()

    path_condition_sequence = reversed_path_sequence[::-1]

    print("Path condition sequence is")
    print(path_condition_sequence)

    for verdict in verdict_dictionary["verdicts"]:

        print("inserting verdict")
        print(verdict)
        print(type(verdict))

        # use the binding space index and the function id to get the binding id
        results = cursor.execute(
            "select * from binding where binding_space_index = ? and function = ?",
            [verdict["bind_space_index"], verdict_dictionary["function_id"]]
        ).fetchall()
        new_binding_id = int(results[0][0])

        print("obtained binding id")

        verdict_value = verdict["verdict"][0]
        verdict_time_obtained = verdict["verdict"][1]
        observations_map = verdict["verdict"][2]
        # Note: path_map already holds integers that are offsets into the program path
        # of the entire function call
        path_map = verdict["verdict"][3]
        collapsing_atom_index = verdict["verdict"][4]
        collapsing_atom_sub_index = verdict["verdict"][5]
        atom_to_state_dict_map = verdict["verdict"][6]

        path_condition_ids = []

        # create the verdict
        # we don't check for an existing verdict - there won't be repetitions here
        cursor.execute(
            "insert into verdict (binding, verdict, time_obtained, function_call, collapsing_atom, collapsing_atom_sub_index) values (?, ?, ?, ?, ?, ?)",
            [new_binding_id, verdict_value, verdict_time_obtained, function_call_id, collapsing_atom_index,
             collapsing_atom_sub_index])
        new_verdict_id = cursor.lastrowid

        print("inserted verdict - now performing observation insertion")

        for atom_index in observations_map:
            # insert observation(s) for this atom_index
            print(observations_map[atom_index])
            for sub_index in observations_map[atom_index].keys():
                last_condition = path_condition_sequence[path_map[atom_index][sub_index]]
                cursor.execute(
                    "insert into observation (instrumentation_point, verdict, observed_value, observation_time, "
                    "observation_end_time, previous_condition, atom_index, sub_index) values(?, ?, ?, ?, ?, ?, ?, ?)",
                    [observations_map[atom_index][sub_index][1], new_verdict_id,
                     str(observations_map[atom_index][sub_index][0]), observations_map[atom_index][sub_index][2],
                     observations_map[atom_index][sub_index][3], last_condition, atom_index, sub_index]
                )
                observation_id = cursor.lastrowid

                # insert assignments (if they don't exist yet), and link them
                # to the observation we just inserted

                state_dict = atom_to_state_dict_map[atom_index][sub_index]
                if state_dict:
                    print(state_dict)
                    for var in state_dict.keys():
                        # check if this assignment already exists
                        assignments = cursor.execute(
                            "select id from assignment where variable = ? and value = ?",
                            [var, pickle.dumps(state_dict[var])]
                        ).fetchall()

                        # either take the existing ID, or insert a new assignment and use the new ID
                        if len(assignments) > 0:
                            # the assignment already exists - get its ID and link it to the observation
                            assignment_id = assignments[0][0]
                        else:
                            # create a new assignment
                            cursor.execute(
                                "insert into assignment (variable, value, type) values(?, ?, ?)",
                                [var, pickle.dumps(state_dict[var]), str(type(state_dict[var]))]
                            )
                            assignment_id = cursor.lastrowid

                        # insert the link
                        cursor.execute(
                            "insert into observation_assignment_pair (observation, assignment) values(?, ?)",
                            [observation_id, assignment_id]
                        )

        # commit for this verdict
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
            "bind_variables": property_dictionary["serialised_bind_variables"],
            "property": property_dictionary["serialised_formula_structure"]
        }
        serialised_structure = json.dumps(serialised_structure)
        cursor.execute("insert into property (hash, serialised_structure) values (?, ?)",
                       [property_dictionary["formula_hash"], serialised_structure])
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
        cursor.execute("insert into function (fully_qualified_name, property) values (?, ?)",
                       [property_dictionary["function"], property_dictionary["formula_hash"]])
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
                       [binding_dictionary["binding_space_index"], binding_dictionary["function"],
                        json.dumps(binding_dictionary["binding_statement_lines"])])
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
        cursor.execute(
            "insert into instrumentation_point (serialised_condition_sequence, reaching_path_length) values (?, ?)",
            [json.dumps(dictionary["serialised_condition_sequence"]), dictionary["reaching_path_length"]])
        new_id = cursor.lastrowid

        # insert the atom-instrumentation point link
        cursor.execute("insert into atom_instrumentation_point_pair (atom, instrumentation_point) values (?, ?)",
                       [dictionary["atom"], new_id])

        # insert the binding-instrumentation point link
        cursor.execute("insert into binding_instrumentation_point_pair (binding, instrumentation_point) values (?, ?)",
                       [dictionary["binding"], new_id])

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
        result = cursor.execute("select * from path_condition_structure where serialised_condition = ?",
                                [dictionary["serialised_condition"]]).fetchall()
        if len(result) > 0:
            # condition already exists - return the existing ID
            return result[0][0]
        else:
            # condition is new - insert it
            cursor.execute("insert into path_condition_structure (serialised_condition) values (?)",
                           [dictionary["serialised_condition"]])
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
    Given a function name, for each transaction, for each function call, list the verdicts.
    """
    connection = get_connection()
    cursor = connection.cursor()

    function_id = \
        cursor.execute("select id from function where fully_qualified_name = ?", [function_name]).fetchall()[0][0]

    bindings = cursor.execute("select * from binding where function = ?", [function_id]).fetchall()

    transactions = cursor.execute("select * from trans").fetchall()
    request_to_verdicts = {}
    for result in transactions:
        request_to_verdicts[result[1]] = {}
        # find the function calls of function_name for this transaction
        calls = cursor.execute("select * from function_call where trans = ?", [result[0]]).fetchall()
        for call in calls:
            request_to_verdicts[result[1]][call[2]] = {}
            for binding in bindings:
                verdicts = cursor.execute("select * from verdict where binding = ? and function_call = ?",
                                          [binding[0], call[0]]).fetchall()
                request_to_verdicts[result[1]][call[2]][binding[0]] = verdicts
                truth_map = {1: True, 0: False}
                request_to_verdicts[result[1]][call[2]][binding[0]] = map(list, request_to_verdicts[result[1]][call[2]][
                    binding[0]])
                for n in range(len(request_to_verdicts[result[1]][call[2]][binding[0]])):
                    request_to_verdicts[result[1]][call[2]][binding[0]][n][1] = truth_map[
                        request_to_verdicts[result[1]][call[2]][binding[0]][n][1]]

    connection.close()

    return request_to_verdicts


def list_transactions(function_id):
    """
    Return a list of all transactions - we may eventually want do to this with a time interval bound.
    """
    connection = get_connection()
    cursor = connection.cursor()

    transactions = cursor.execute("select * from trans").fetchall()

    # list only the requests for which there is a call to the function with function_id
    final_requests = []
    for request in transactions:
        calls_with_function_id = cursor.execute("select * from function_call where function = ? and trans = ?",
                                                [function_id, request[0]]).fetchall()
        if len(calls_with_function_id) > 0:
            final_requests.append(request)

    connection.close()
    print(final_requests)

    return final_requests


def list_calls_during_request(transaction_id, function_name):
    """
    Given an transaction id, list the function calls of the given function during that request.
    """
    connection = get_connection()
    cursor = connection.cursor()

    function_calls = cursor.execute("select * from function_call where trans = ? and function = ?",
                                    [transaction_id, function_name]).fetchall()

    connection.close()

    return function_calls


def list_verdicts_from_function_call(function_call_id):
    """
    Given a function call id, return all the verdicts reached during this function call.
    """
    connection = get_connection()
    cursor = connection.cursor()

    verdicts = cursor.execute("select binding.binding_statement_lines, verdict.verdict, verdict.time_obtained from " + \
                              "(verdict inner join binding on verdict.binding=binding.id) where verdict.function_call = ?",
                              [function_call_id]).fetchall()

    connection.close()

    return verdicts


def web_list_functions():
    """
    Return a list of all functions found.
    """

    print("listing functions")

    connection = get_connection()
    cursor = connection.cursor()

    functions = cursor.execute(
        "select function.id, function.fully_qualified_name, function.property, property.serialised_structure from " + \
        "(function inner join property on function.property=property.hash)").fetchall()

    # process the functions into a hierarchy by splitting the function names up by dots
    dictionary_tree_structure = {}
    print("building function tree")
    for function in functions:

        print(function)

        path = function[1].split(".")
        if not (dictionary_tree_structure.get(path[0])):
            dictionary_tree_structure[path[0]] = {}
        current_hierarchy_step = dictionary_tree_structure[path[0]]
        # iterate through the rest of the path
        for item in path[1:-1]:
            if not (current_hierarchy_step.get(item)):
                current_hierarchy_step[item] = {}
            current_hierarchy_step = current_hierarchy_step[item]

        if current_hierarchy_step.get(path[-1]):
            current_hierarchy_step[path[-1]].append(function)
        else:
            current_hierarchy_step[path[-1]] = [function]

    print(dictionary_tree_structure)

    connection.close()

    return dictionary_tree_structure


def get_transaction_function_call_pairs(verdict, path):
    """
    For the given verdict and path pair, find all the function calls inside that path that
    result in a verdict matching the one given.

    To do this, we first find all the functions that match the path given.
    """
    connection = get_connection()
    cursor = connection.cursor()

    path = "%s%%" % path

    truth_map = {"violating": 0, "not-violating": 1}

    final_map = {}

    # note that a function is unique wrt a property - so each row returned here is coupled with a single property
    functions = cursor.execute("select * from function where fully_qualified_name like ?", [path]).fetchall()

    # Now, get all the calls to these functions and, for each call, find all the verdicts and organise them by binding

    final_map["functions"] = {}
    for function in functions:
        final_map["functions"][function[0]] = {"calls": {}, "property": {}, "fully_qualified_name": function[1]}
        data_found_for_function = False

        # get the property string representation
        property_id = function[2]
        property_info = json.loads(
            cursor.execute("select * from property where hash = ?", [property_id]).fetchall()[0][1])
        final_map["functions"][function[0]]["property"] = property_info

        # get the calls
        calls = cursor.execute("select * from function_call where function = ?", [function[0]]).fetchall()
        for call in calls:
            data_found_for_call = False
            final_map["functions"][function[0]]["calls"][call[0]] = {"bindings": {}, "time": call[2]}
            bindings = cursor.execute("select * from binding where function = ?", [function[0]]).fetchall()
            for binding in bindings:
                verdicts = cursor.execute(
                    "select * from verdict where binding = ? and function_call = ? and verdict = ?",
                    [binding[0], call[0], truth_map[verdict]]).fetchall()
                verdict_tuples = map(lambda row: (row[2], row[3]), verdicts)
                if len(verdict_tuples) > 0:
                    final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]] = {"verdicts": [],
                                                                                                     "lines": binding[
                                                                                                         3]}
                    final_map["functions"][function[0]]["calls"][call[0]]["bindings"][binding[0]][
                        "verdicts"] = verdict_tuples
                    data_found_for_call = True
                    data_found_for_function = True

            if not (data_found_for_call):
                del final_map["functions"][function[0]]["calls"][call[0]]

        if not (data_found_for_function):
            del final_map["functions"][function[0]]

    return final_map


# these two functions search the database for the given query
# the difference is that query_db_one returns one row of the database
# while query_db_all returns all the rows that match the query
def query_db_one(query_string, arg):
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    # enables saving the rows as a dictionary with name of column as key
    cursor = connection.cursor()
    list1 = cursor.execute(query_string, arg)
    f = list1.fetchone()
    connection.close()
    if f == None: return ("None")
    return json.dumps([dict(f)])


def query_db_all(query_string, arg):
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    list1 = cursor.execute(query_string, arg)
    functions = list1.fetchall()
    connection.close()
    if functions == None: return ("None")
    return json.dumps([dict(f) for f in functions])


def list_functions2():
    query_string = "select * from function;"
    return query_db_all(query_string, [])


def list_calls_function(function_name):
    # based on the name of the function, list all function calls of the function with that name
    query_string = """select function_call.id, function_call.function, function_call.time_of_call, 
    function_call.end_time_of_call, function_call.trans from (function inner join function_call on 
    function.id=function_call.function) where function.fully_qualified_name like ? """
    return query_db_all(query_string, [function_name])


def list_calls_transaction(transaction_id):
    # list all function_calls during the given transaction
    query_string = """
    select function_call.id, function_call.function, function_call.time_of_call,
    function_call.end_time_of_call, function_call.trans
    from (trans inner join function_call on
        trans.id=function_call.trans)
    where trans.id=?"""
    return query_db_all(query_string, [transaction_id])


def list_calls_transactionid(transaction_id, function_id):
    # a combination of the previous two functions: lists calls of given function during the given request
    query_string = "select * from function_call where trans=? and function=?"
    return query_db_all(query_string, [transaction_id, function_id])


def list_calls_verdict(function_id, verdict_value):
    # returns a list of dictionaries with calls of the given function
    # such that their verdict value is 0 or 1 (verdict_value)
    query_string = """select function_call.id, function_call.function,
    function_call.time_of_call, function_call.end_time_of_call,	function_call.trans from
    function_call inner join verdict on verdict.function_call=function_call.id
    inner join function on function_call.function=function.id
    where function.id=? and verdict.verdict=?"""
    return query_db_all(query_string, [function_id, verdict_value])


def get_f_byname(function_name):
    query_string = "select * from function where fully_qualified_name like ?"
    return query_db_all(query_string, [function_name])


def get_f_byid(function_id):
    query_string = "select * from function where id like ?"
    return query_db_one(query_string, [function_id])


def get_transaction_byid(transaction_id):
    query_string = "select * from trans where id=?"
    return query_db_one(query_string, [transaction_id])


def get_call_byid(call_id):
    query_string = "select * from function_call where id=?"
    return query_db_one(query_string, [call_id])


def get_transaction_bytime(time):
    query_string = "select * from trans where time_of_transaction=?"
    return query_db_one(query_string, [time])


def get_verdict_byid(verdict_id):
    query_string = "select * from verdict where id=?"
    return query_db_one(query_string, [verdict_id])


def get_atom_byid(atom_id):
    query_string = "select * from atom where id=?"
    return query_db_one(query_string, [atom_id])


def get_atom_by_index_and_property(atom_index, property_hash):
    query_string = """select * from atom where index_in_atoms=?
    and property_hash=?"""
    return query_db_one(query_string, [atom_index, property_hash])


def list_atoms_verdict(verdict_value):
    query_string = """select atom.id,atom.property_hash,atom.serialised_structure,atom.index_in_atoms
    from (verdict inner join atom on verdict.collapsing_atom=atom.index_in_atoms)
    where verdict.verdict=?"""
    return query_db_all(query_string, [verdict_value])


def get_falsifying_observation_call(call_id):
    # inner join three tables: observation-verdict-function_call
    # find rows corresponding to the given call_id and with verdict value zero
    # order by verdict limit 1 in order to find the first one wrt verdicts
    query_string = """select observation.id,observation.instrumentation_point,
    observation.verdict,observation.observed_value,observation.atom_index,
    observation.previous_condition from
    (observation inner join verdict on observation.verdict=verdict.id
    inner join function_call on verdict.function_call=function_call.id)
    where function_call.id=? and verdict.verdict=0
    order by verdict.time_obtained limit 1"""
    return query_db_one(query_string, [call_id])


def get_property_byhash(hash):
    query_string = "select * from property where hash like ?"
    return query_db_one(query_string, [hash])


def get_point_byid(id):
    query_string = "select * from instrumentation_point where id=?"
    return query_db_one(query_string, [id])


def get_binding_byid(id):
    query_string = "select * from binding where id=?"
    return query_db_one(query_string, [id])


def get_bindings_from_function_property_pair(id):
    query_string = "select * from binding where function=?"
    return query_db_all(query_string, [id])


def get_observation_byid(id):
    query_string = "select * from observation where id=?"
    return query_db_one(query_string, [id])


def get_assignment_byid(id):
    query_string = "select * from assignment where id=?"
    return query_db_one(query_string, [id])


def get_pcs_byid(id):
    query_string = "select * from path_condition_structure where id=?"
    return query_db_one(query_string, [id])


def get_pathcon_byid(id):
    query_string = "select * from path_condition where id=?"
    return query_db_one(query_string, [id])


def get_searchtree_byid(id):
    query_string = "select * from search_tree where id=?"
    return query_db_one(query_string, [id])


def get_searchtreevertex_byid(id):
    query_string = "select * from search_tree_vertex where id=?"
    return query_db_one(query_string, [id])


def get_intersection_byid(id):
    query_string = "select * from intersection where id=?"
    return query_db_one(query_string, [id])


def list_assignments_obs(observation_id):
    query_string = """select assignment.id, assignment.variable,
    assignment.value,assignment.type
    from assignment inner join observation_assignment_pair
    on assignment.id=observation_assignment_pair.assignment
    where observation_assignment_pair.observation =?"""
    return query_db_all(query_string, [observation_id])


def list_verdicts_byvalue(value):
    query_string = "select * from verdict where verdict.verdict=?"
    return query_db_all(query_string, [value])


def list_verdicts_function_property_byvalue(value):
    query_string = """select verdict.id, verdict.binding, verdict.verdict,
    verdict.time_obtained, function_call.function, function.fully_qualified_name,
    function_call.time_of_call, function.property
    from (verdict inner join function_call on verdict.function_call=function_call.id
    inner join function on function_call.function=function.id)
    where verdict.verdict=?"""
    return query_db_all(query_string, [value])


def list_verdicts_call(call_id):
    query_string = "select * from verdict where function_call=?"
    return query_db_all(query_string, [call_id])


def list_verdicts_from_binding(binding_id):
    query_string = "select * from verdict where binding=?"
    return query_db_all(query_string, [binding_id])


def list_observations_call(call_id):
    query_string = """select observation.id, observation.instrumentation_point,
    observation.verdict,observation.observed_value,observation.atom_index,
    observation.previous_condition from
    observation inner join verdict on observation.verdict=verdict.id
    inner join function_call on verdict.function_call=function_call.id
    where function_call.id=?"""
    return query_db_all(query_string, [call_id])


def list_observations():
    query_string = "select * from observation;"
    return query_db_all(query_string, [])


def list_observations_of_point(point_id):
    query_string = """select observation.id, observation.instrumentation_point,
    observation.verdict,observation.observed_value,observation.atom_index,
    observation.previous_condition from observation
    where observation.instrumentation_point=?"""
    return query_db_all(query_string, [point_id])


def list_verdicts_with_value_of_call(call_id, verdict_value):
    query_string = "select * from verdict where function_call=? and verdict=?"
    return query_db_all(query_string, [call_id, verdict_value])


def list_verdicts_of_function(function_id):
    query_string = """select * from verdict inner join binding
    on verdict.binding=binding.id
    where binding.function=?"""
    return query_db_all(query_string, [function_id])


def list_verdicts_of_function_with_value(function_id, verdict_value):
    query_string = """select * from verdict inner join binding
    on verdict.binding=binding.id
    where binding.function=? and verdict.verdict=?"""
    return query_db_all(query_string, [function_id, verdict_value])


def list_functions():
    query_string = "select * from function"
    return query_db_all(query_string, [])


def get_assignment_dict_from_observation(id):
    """
    Given an observation ID, construct a dictionary mapping
    variable names to values collected during monitoring.
    """
    connection = get_connection()
    cursor = connection.cursor()
    list1 = cursor.execute(
        """
select assignment.variable, assignment.value, assignment.type from
((observation inner join observation_assignment_pair
        on observation_assignment_pair.observation == observation.id)
        inner join assignment
            on assignment.id == observation_assignment_pair.assignment)
where observation.id = ?
""",
        [id]
    ).fetchall()
    final_dict = {}
    for row in list1:
        final_dict[row[0]] = (row[1], row[2])
    connection.close()
    return json.dumps(final_dict)


def get_observations_from_verdict(verdict_id):
    """
    Given a verdict ID, return a list of verdict dictionaries.
    """
    query_string = "select * from observation where verdict = ?"
    return query_db_all(query_string, [verdict_id])


"""
Path reconstruction functions.
"""


def get_serialised_condition_from_id(id):
    """
    Given an ID, get the serialised condition that can be used in path reconstruction.
    """
    connection = get_connection()
    cursor = connection.cursor()

    serialised_condition = cursor.execute(
        "select serialised_condition from path_condition_structure where id = ?",
        [id]
    ).fetchone()[0]

    connection.close()

    return serialised_condition


def get_path_conditions_from_observation(id):
    """
    Given an observation ID, find the sequence of path conditions leading to it.
    To do this, we have to go backwards, since we first find the path condition before the observation,
    and then find each successive path condition until we reach the beginning (no previous condition).
    """
    connection = get_connection()
    cursor = connection.cursor()
    result = cursor.execute(
        """
select path_condition.id, path_condition.serialised_condition from
(path_condition inner join observation
    on path_condition.id = observation.previous_condition)
where observation.id = ?
""",
        [id]
    ).fetchone()

    while result:

        previous_path_condition = result[0]
        try:
            reversed_path_conditions.append(result[1])
        except:
            reversed_path_conditions = [result[1]]
        print("checking for path_condition with next_path_condition = %i" % previous_path_condition)
        result = cursor.execute(
            "select id, serialised_condition from path_condition where next_path_condition = ?",
            [previous_path_condition]
        ).fetchone()

    connection.close()

    return json.dumps(map(get_serialised_condition_from_id, reversed_path_conditions[::-1]))


def compute_intersection(s, instrumentation_point_id):
    """
    Given a list s of observations and an instrumentation point ID, compute the intersection
    of the reconstructed paths using existing results as much as possible.
    """
    connection = get_connection()
    cursor = connection.cursor()

    instrumentation_point_path_length = int(
        cursor.execute(
            "select reaching_path_length from instrumentation_point where id = ?",
            [instrumentation_point_id]
        ).fetchall()[0][0]
    )

    # we'll need this at the end when we construct maps from observation ids
    # to values they give each parameter
    observation_list_copy = [obs for obs in s]

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
    search_trees = cursor.execute("select * from search_tree where instrumentation_point = ?",
                                  [instrumentation_point_id]).fetchall()

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
        if not (root_observation_id):
            # there were search trees for this instrumentation point, but none had a root we could use
            # so now we construct a new search tree whose root is s[0]
            # we then attach condition_sequence to the new leaf node
            print("no suitable search tree found - constructing a new one")
            # reconstruct the paths, compute the intersection and convert the resulting parametric path
            # into a condition sequence
            condition_sequence = construct_new_search_tree(connection, cursor, scfg, s[0], s[1:],
                                                           instrumentation_point_id)

        else:
            print("suitable search tree found - attempting traversal")
            # if we found a search tree, traverse it and see if the intersection for this set of observations
            # has already been computed
            # root already exists, so remove it
            s.remove(root_observation_id)
            # here, we iterate until there are no observations remaining
            # each iteration, we go through the remaining observations and see if we can traverse the tree further
            parent_vertex_id = root_vertex_id
            nothing_added = True
            most_recent_id = None

            while len(s) > 0:

                print("remaining observations %s" % str(s))

                # search for a next vertex that we can follow
                next_vertex = None

                for obs in s:
                    print("looking for vertices with observation %i and parent %i" % (obs, parent_vertex_id))
                    next_vertex_list = cursor.execute(
                        "select * from search_tree_vertex where observation = ? and parent_vertex = ?",
                        [obs, parent_vertex_id]).fetchall()
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
                    # if we make it to the end of the loop without hitting a leaf, we'll need to remember the ID of the
                    # vertex we reached so we can get its intersection
                    most_recent_id = parent_vertex_id
                else:
                    nothing_added = False
                    # there's no vertex we can follow with the observations we have
                    # the only way to continue is to extend the tree
                    # we choose the first element from the remaining set of observations as a starting point
                    print("can't progress! doing insertion for observation id %i with parent vertex %i" % (
                        s[0], parent_vertex_id))

                    # we take the intersection stored at the leaf we found (guaranteed to exist)
                    intersection_condition_sequence = cursor.execute(
                        """
select intersection.condition_sequence_string from
(search_tree_vertex inner join intersection on intersection.id == search_tree_vertex.intersection)
where search_tree_vertex.id = ?
""",
                        [parent_vertex_id]
                    ).fetchall()[0][0]
                    intersection_condition_sequence = json.loads(intersection_condition_sequence)
                    deserialised_condition_sequence = map(deserialise_condition, intersection_condition_sequence)
                    deserialised_condition_sequence = deserialised_condition_sequence[1:]

                    print("deserialised condition sequence")
                    print(deserialised_condition_sequence)

                    # we reconstruct the path through the scfg based on this condition sequence
                    parametric_path = edges_from_condition_sequence(scfg, deserialised_condition_sequence,
                                                                    instrumentation_point_path_length)

                    print("parametric path derived is")
                    print(parametric_path)

                    print("building parametric parse tree")
                    parametric_parse_tree = ParseTree(parametric_path, grammar_rules_map, scfg.starting_vertices,
                                                      parametric=True)

                    # we now need to form the intersection parse tree of the remaining observations,
                    # then intersect that with the parse tree from the existing subpath of the search tree
                    # we then convert that to a condition sequence, and associated this sequence with the new leaf
                    # of the search tree

                    previous_intersection_result = parametric_parse_tree

                    # acts as a map from observation id index to intersection
                    intersections = [parametric_parse_tree]
                    for obs in s:
                        path = reconstruct_path(cursor, scfg, obs)
                        new_parse_tree = ParseTree(path, scfg.derive_grammar(), scfg.starting_vertices, parametric=True)
                        new_intersection = previous_intersection_result.intersect([new_parse_tree])
                        intersections.append(new_intersection)

                    condition_sequences = []
                    for intersection in intersections:
                        parametric_path = intersection.read_leaves()
                        condition_sequences.append(path_to_condition_sequence(cursor, parametric_path))

                    print(condition_sequences)

                    print("adding a new path for remaining observations %s" % str(s))
                    insert_observations_from_vertex(connection, cursor, s, parent_vertex_id, condition_sequences)

                    # return the last condition sequence we computed - this is from the leaf
                    condition_sequence = condition_sequences[-1]
                    break

            if nothing_added:
                print("intersection already exists in database - no need to compute it")
                condition_sequence = cursor.execute(
                    """
select intersection.condition_sequence_string from
(intersection inner join search_tree_vertex on search_tree_vertex.intersection = intersection.id)
where search_tree_vertex.id = ?
""",
                    [most_recent_id]
                ).fetchall()[0][0]
                condition_sequence = json.loads(condition_sequence)

    else:
        # no search tree was found for this instrumentation point
        # compute the intersection, then construct the tree and add a link to the intersection
        # to the leaf vertex
        print("no search tree found for observation sequence %s - constructing intersection, then a new tree" % str(s))

        # if we didn't find a search tree, then the intersection isn't computed yet (since we check
        # for search trees whose roots are any element in the list of observations we have).
        # once the search tree is constructed, condition_sequence will be attached to the new leaf node

        # reconstruct the paths, compute the intersection and convert the resulting parametric path
        # into a condition sequence
        condition_sequence = construct_new_search_tree(connection, cursor, scfg, s[0], s[1:], instrumentation_point_id)

    # using condition_sequence, reconstruct the parametric path
    # then, for each parameter, find its path through the parse tree
    # then follow this path through the parse tree of each reconstructed path
    # to determine path parameter values

    print("determining path parameters wrt parametric path %s" % str(condition_sequence))

    final_parametric_path = edges_from_condition_sequence(scfg, condition_sequence[1:],
                                                          instrumentation_point_path_length)
    intersection_parse_tree = ParseTree(final_parametric_path, grammar_rules_map, scfg.starting_vertices,
                                        parametric=True)
    paths = reconstruct_paths(cursor, scfg, observation_list_copy)
    parse_trees = map(lambda path: ParseTree(path, grammar_rules_map, scfg.starting_vertices), paths)
    parameter_paths = []
    intersection_parse_tree.get_parameter_paths(intersection_parse_tree._root_vertex, [], parameter_paths)
    parameter_subtrees = {}
    for (n, parameter_path) in enumerate(parameter_paths):
        parameter_subtrees[n] = {}
    for (m, parse_tree) in enumerate(parse_trees):
        for (n, parameter_path) in enumerate(parameter_paths):
            subpath = parse_tree.get_parameter_subtree(parameter_path).read_leaves()
            print("parameter value for parse tree %i" % m)
            subpath_condition_sequence = path_to_condition_sequence(cursor, subpath, parametric=True)
            parameter_subtrees[n][m] = subpath_condition_sequence

    print(parameter_paths)

    final_data = {
        "intersection_condition_sequence": condition_sequence,
        "parameter_maps": parameter_subtrees
    }

    connection.close()

    return final_data


def compute_condition_sequence_and_path_length(observation_id):
    """
    Given an observation ID, find the path condition sequence leading to that observation.
    """

    connection = get_connection()
    cursor = connection.cursor()

    condition_sequence_and_path_length = observation_id_to_condition_sequence_and_path_length(cursor, observation_id)

    connection.close()

    return condition_sequence_and_path_length
