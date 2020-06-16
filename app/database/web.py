"""
Module to provide functions for the web analysis tool to use.

TODO: add quotes where they should be in the specification, other states?
"""
from .utils import get_connection
import json
import dateutil.parser
import pickle
import base64
from VyPR.monitor_synthesis.formula_tree import *
from VyPR.QueryBuilding.formula_building import *
from VyPR.SCFG.construction import *
import app
import ast
import os

HTML_ON = False


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

    print("getting transactions with function id %s" % function_id)

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


def list_calls_from_id(function_id):
    """
    Given a function id (which implicitly also fixes a property), list the calls found.
    """
    connection = get_connection()
    cursor = connection.cursor()
    function_calls = cursor.execute("select * from function_call where function = ?", [function_id]).fetchall()
    # perform any processing on each function call that we need
    modified_calls = []
    for function_call in function_calls:
        new_call = list(function_call)
        new_call.append(
            (dateutil.parser.parse(new_call[3]) - dateutil.parser.parse(new_call[2])).total_seconds()
        )
        new_call[2] = dateutil.parser.parse(new_call[2]).strftime("%d/%m/%Y %H:%M:%S")
        new_call[3] = dateutil.parser.parse(new_call[3]).strftime("%d/%m/%Y %H:%M:%S")
        modified_calls.append(new_call)
    return modified_calls


def list_calls_during_request(transaction_id, function_name):
    """
    Given an transaction id, list the function calls of the given function during that request.
    """
    connection = get_connection()
    cursor = connection.cursor()

    print("getting calls")
    function_calls = cursor.execute("select * from function_call where trans = ? and function = ?",
                                    [transaction_id, function_name]).fetchall()

    connection.close()

    return function_calls

def list_calls_in_interval(start, end, function_id):
    """start and end are strings in dd/mm/yyyy hh:mm:ss format"""
    connection = get_connection()
    cursor = connection.cursor()

    start_timestamp = dateutil.parser.parse(start.replace("%20"," ")).strftime("%Y-%m-%dT%H:%M:%S")
    end_timestamp = dateutil.parser.parse(end.replace("%20", " ")).strftime("%Y-%m-%dT%H:%M:%S")

    function_calls = cursor.execute("""select id from function_call where time_of_call>=?
        and end_time_of_call <= ? and function=?""", [start_timestamp, end_timestamp, function_id]).fetchall()

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
        """select function.id, function.fully_qualified_name, property.hash, property.serialised_structure
            from (function inner join function_property_pair on function.id==function_property_pair.function)
            inner join property on function_property_pair.property_hash=property.hash""").fetchall()

    # process the functions into a hierarchy by splitting the function names up by dots
    dictionary_tree_structure = {}
    print("building function tree")

    for function in functions:

        # first, we want to check if the specification is referring to 'fake_vypr_var'
        # if it is, we will not store this function in the tree
        #  because the specification given by the user was empty
        bind_var = pickle.loads(base64.b64decode(json.loads(function[3])["bind_variables"]))
        var = bind_var.items()[0]
        print(type(var[1]))
        if (type(var[1]) is StaticState):
            if (var[1]._name_changed == 'fake_vypr_var'): continue


        print(function[1])

        full_name = function[1]

        # the hierarchy also includes the machine name (server/client) separated by a hyphen
        machine_rest = full_name.split("-")
        machine = [machine_rest[0]]

        #in case it does not
        if len(machine_rest) == 1:
            path_rest =machine_rest[0].split(".")
        else:
            path_rest = machine_rest[1].split(".")

        # finally, the name of the function is separated with a colon sometimes
        last = path_rest[-1].split(":")
        path_rest = path_rest[0:-1] + last
        path = machine + path_rest

        print(path)


        # constructing the tree

        if not (dictionary_tree_structure.get(path[0])):
            dictionary_tree_structure[path[0]] = {}
        current_hierarchy_step = dictionary_tree_structure[path[0]]
        # iterate through the rest of the path
        for item in path[1:-1]:
            if not (current_hierarchy_step.get(item)):
                current_hierarchy_step[item] = {}
            current_hierarchy_step = current_hierarchy_step[item]


        # storing (hash,specification) as a leaf of the tree

        hash = function[2]
        prop = pickle.loads(base64.b64decode(json.loads(function[3])["property"]))
        # bind_var was decoded in the first step of the loop

        global atoms_list
        atoms_list = []
        property_to_atoms_list(prop)

        if HTML_ON:
            atom_str = prop.HTMLrepr()
            spec = ''
            vars = ''

            # vars will save a list of variables as "x, y, z" - used later in lambda
            # spec begins with Forall(...) - each variable generates one of these
            for var in bind_var.items():
                print(var[1].my_repr_function())
                atom_str = atom_str.replace(str(var[1]), var[0], 1)
                if spec:
                    vars += ", "
                spec += '<p class="list-group-item-text code" id="bind-variable-name-' + var[0] +\
                    '">Forall(%s).\ </p>' % var[1].my_repr_function()
                vars += var[0]

            for var in bind_var.items():
                atom_str = atom_str.replace(str(var[1]),var[0])

            # finally, add the condition stored in atom_str to the specification
            spec +="""<p class="list-group-item-text code">Check( </p>
                <p class="list-group-item-text code">&nbsp;&nbsp;lambda %s : ( </p>
                <p class="list-group-item-text code">&nbsp;&nbsp;&nbsp;&nbsp; %s </p>
                <p class="list-group-item-text code">&nbsp;&nbsp;) </p>
                <p class="list-group-item-text code">)</p>""" % (vars, atom_str)

        else:
            atom_str = prop.HTMLrepr()
            vars = ''
            foralls = []

            # vars will save a list of variables as "x, y, z" - used later in lambda
            # spec begins with Forall(...) - each variable generates one of these
            for var in bind_var.items():
                atom_str = atom_str.replace(str(var[1]), var[0], 1)
                if vars:
                    vars += ", "
                vars += var[0]
                foralls.append({"var_id": var[0], "var_forall": var[1].my_repr_function()})

            for var in bind_var.items():
                atom_str = atom_str.replace(str(var[1]),var[0])

            # finally, add the condition stored in atom_str to the specification
            spec = {"vars": vars, "foralls": foralls, "atom_str": atom_str}

        # and store pairs (hash,specification) as leaves
        if current_hierarchy_step.get(path[-1]):
            current_hierarchy_step[path[-1]].append([function[0], hash, spec])
        else:
            current_hierarchy_step[path[-1]] = [[function[0], hash, spec]]

    # pprint(dictionary_tree_structure)
    #dictionary_tree_structure["client"] = {"app": [[function[0], hash, spec]]}
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


def get_code(function_id):

    connection = get_connection()
    cursor = connection.cursor()

    function = cursor.execute("""select function.fully_qualified_name, function_property_pair.property_hash
    from (function inner join function_property_pair on function.id==function_property_pair.function)
    where function.id = ?""", [function_id]).fetchone()
    func = function[0]

    #check if the monitored service path was given as an argument
    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please parse the monitored service path as an argument (--path)"}
        return error_dict

    if "-" in func[0:func.index(".")]:
        func = func[func.index("-")+1:]

    module = func[0:func.rindex(".")]
    func = func[func.rindex(".") + 1:]
    file_name = module.replace(".", "/") + ".py.inst"
    # extract asts from the code in the file
    code = "".join(open(os.path.join(location, file_name), "r").readlines())
    asts = ast.parse(code)
    qualifier_subsequence = get_qualifier_subsequence(func)
    func = func.replace(":", ".")
    function_name = func.split(".")

    # find the function definition
    actual_function_name = function_name[-1]
    hierarchy = function_name[:-1]
    current_step = asts.body

    # traverse sub structures
    for step in hierarchy:
        current_step = filter(lambda entry: (type(entry) is ast.ClassDef and entry.name == step), current_step)[0]

    # find the final function definition
    function_def = list(filter(lambda entry: (type(entry) is ast.FunctionDef and entry.name == actual_function_name),
              current_step.body if type(current_step) is ast.ClassDef else current_step))[0]

    #we want to now exact line numbers of these ast objects
    start = function_def.lineno - 1
    end = function_def.body[-1].lineno - 1

    lines = code.split('\n')

    #take the section of code between the line numbers - this is the source code
    #of the function of interest without the rest of the code
    f_code = lines[start:end]

    dict = {"start_line" : start+1,
            "end_line": end+1,
            "code" : f_code}


    #now get data about bindings and add them to the dictionary structure
    bindings = cursor.execute("""select id, binding_space_index, binding_statement_lines from binding
                        where function = ?""", [function_id]).fetchall()
    bindings_list = []
    for b in bindings:
        d = {"id" : b[0], "binding_space_index" : b[1], "binding_statement_lines" : json.loads(b[2])}
        bindings_list.append(d)

    dict["bindings"] = bindings_list

    connection.close()
    return dict


def get_calls_data(ids_list):
    """
    Given a list of function call IDs, using path condition sequence,
     reconstruct the path taken to an instrumentation point

    """
    #print(ids_list)
    connection = get_connection()
    cursor = connection.cursor()

    ids = list_to_sql_string(ids_list)

    query_string = "select id, function, time_of_call, end_time_of_call, trans, path_condition_id_sequence from function_call where id in %s;" % ids
    calls = cursor.execute(query_string).fetchall()
    #print(calls)


    #check if the monitored service path was given as an argument
    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please parse the monitored service path as an argument (--path)"}
        return error_dict


    # get the scfg of the function called by these calls and get all their path_condition_id_sequences
    # but without duplicate instances of sequences - store them as keys in dictionary 'sequences'
    # the corresponding value is a list of the IDs of the calls that generated the sequence (key)
    function = cursor.execute("""select function.fully_qualified_name, function_property_pair.property_hash
    from (function inner join function_property_pair on function.id==function_property_pair.function)
    where function.id = ?""", [calls[0][1]]).fetchone()
    func = function[0]
    scfg = get_scfg(func, location)
    sequences = {}
    inst_point_ids = set()
    lines = set()

    for call in calls:
        seq = call[5] # get the list of path condition ids
        if seq not in sequences.keys():
            sequences[seq]=[call[0]]
        else:
            sequences[seq].append(call[0])


    for seq in sequences:
        #if there are more calls that generated the sequence, take the first one
        call_id = sequences[seq][0]
        # get the list of path conditions defined by the ids above
        subchain = []
        for condition in json.loads(seq):
            query_string = "select serialised_condition from path_condition_structure where id = %s;" % condition
            condition_string = cursor.execute(query_string).fetchone()[0]
            subchain.append(condition_string)
        print(subchain)

        # get observations generated during this function call
        observations = cursor.execute("""select observation.id, observation.instrumentation_point,
            observation.previous_condition_offset from
            (observation inner join verdict on observation.verdict == verdict.id)
            where verdict.function_call = ?""", [call_id]).fetchall()

        # reconstruct the path to each observation to find the line in the code
        # that generates that observation (last element in the found path)
        for obs in observations:
            instrumentation_point_path_length = cursor.execute("""select reaching_path_length from
                instrumentation_point where id = ?""", [obs[1]]).fetchone()
            path = edges_from_condition_sequence(scfg, subchain[1:(obs[2]+1)], instrumentation_point_path_length[0])
            path_elem = path[-1]
            inst_point_ids.add(obs[1])
            #TODO: path_elem type can be edge(_instruction), but also vertex(_structure_obj)
            lines.add((obs[1],path_elem._instruction.lineno))

    print("Instrumentation points' IDs: %s" % inst_point_ids)
    print("Pairs (instrumentation point ID, line number): %s" % lines)


    # now we want to group the instrumenation points by bindings and atoms

    # first, get the list of all (binding, atom_index, sub_index, instrumentation_point) combinations
    # then, create a dictionary whose keys will be binding IDs
    # and the value for that key is a dict with atom indices as keys, and then subatom indices
    # finally, value stored in the leaf of this tree is a list of instrumentation points and line numbers
    # (also stored as dictionaries)
    query_string = """select distinct verdict.binding, observation.atom_index, observation.sub_index,
    instrumentation_point.id, instrumentation_point.serialised_condition_sequence, instrumentation_point.reaching_path_length
    from ((observation inner join verdict on observation.verdict == verdict.id) inner join
    instrumentation_point on observation.instrumentation_point == instrumentation_point.id)
    where observation.instrumentation_point in %s""" % list_to_sql_string(inst_point_ids)
    binding_atom_list = cursor.execute(query_string).fetchall()

    new_list = []
    for elem in binding_atom_list:
        elem = list(elem)
        tmp = cursor.execute("""select binding_space_index from
            binding where id=? and function=?""", [elem[0],calls[0][1]]).fetchone()[0]
        elem[0] = tmp
        new_list.append(elem)

    binding_atom_list = new_list

    tree = {}

    for elem in binding_atom_list:
        if elem[0] not in tree.keys():
            tree[elem[0]] = {}

    for key in tree.keys():
        subtree = tree[key]
        for elem in binding_atom_list:
            if elem[1] not in subtree.keys():
                subtree[elem[1]] = {}

    for elem in binding_atom_list:
        tree[elem[0]][elem[1]][elem[2]] = []

    for elem in binding_atom_list:
        dict = {"id" : elem[3],
                "serialised_condition_sequence" : elem[4],
                "reaching_path_length" : elem[5],
                "code_line" : None}
        for pair in lines:
            if (pair[0]==dict["id"]):
                dict["code_line"] = pair[1]

        tree[elem[0]][elem[1]][elem[2]].append(dict)

    for binding_key in tree.keys():
        print(binding_key)
        subtree = tree[binding_key]
        bind_lines = json.loads(cursor.execute("""select binding_statement_lines from binding
            where binding_space_index=? and function=?""", [binding_key, calls[0][1]]).fetchone()[0])
        print(bind_lines)
        print(type(bind_lines))
        subtree["-1"] = {"-1" : []}
        for line in bind_lines:
            dict = {"id": None, "serialised_condition_sequence": None, "reaching_path_length": None,
                            "code_line": line}
            subtree["-1"]["-1"].append(dict)

    print(tree)

    return tree


def get_atom_type(atom_index, inst_point_id):
    connection = get_connection()
    cursor = connection.cursor()

    #atom_index defines an atom uniquely provided that we know the property
    prop_hash = cursor.execute("""select distinct function_property_pair.property_hash from
    (((function_property_pair inner join function_call on function_property_pair.function==function_call.function)
    inner join verdict on function_call.id==verdict.function_call) inner join observation
       on observation.verdict==verdict.id) where observation.instrumentation_point=?""",
       [inst_point_id]).fetchone()[0]

    print(prop_hash)
    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    atom_deserialised = pickle.loads(base64.b64decode(atom_structure))
    print(type(atom_deserialised))

    if type(atom_deserialised) in [StateValueEqualToMixed, StateValueLengthLessThanStateValueLengthMixed,
        TransitionDurationLessThanTransitionDurationMixed, TransitionDurationLessThanStateValueMixed,
        TransitionDurationLessThanStateValueLengthMixed]:
        return 'mixed'

    elif type(atom_deserialised) in [TimeBetweenInInterval, TimeBetweenInOpenInterval]:
        return 'timeBetween'

    else:
        return 'simple'

    connection.close()

def get_plot_data_simple(dict):
    connection = get_connection()
    cursor = connection.cursor()
    print(dict)
    calls_list = dict["calls"]
    binding_index = dict["binding"]
    atom_index = dict["atom"]
    sub_index = dict["subatom"]
    points_list = dict["points"]

    query_string = """select observation.observed_value, observation.observation_time,
        observation.observation_end_time, verdict.verdict
        from ((observation inner join verdict on observation.verdict==verdict.id)
        inner join binding on verdict.binding==binding.id) where observation.instrumentation_point in %s
        and observation.atom_index = %s and observation.sub_index = %s and verdict.function_call in %s
        and binding.binding_space_index = %s order by observation.observation_time;""" % (
            list_to_sql_string(points_list), atom_index, sub_index,
            list_to_sql_string(calls_list), binding_index)
    result = cursor.execute(query_string).fetchall()

    prop_hash = cursor.execute("""select distinct function_property_pair.property_hash from
    (((function_property_pair inner join function_call on function_property_pair.function==function_call.function)
    inner join verdict on function_call.id==verdict.function_call) inner join observation
       on observation.verdict==verdict.id) where observation.instrumentation_point=?""",
       [points_list[0]]).fetchone()[0]

    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    formula = pickle.loads(base64.b64decode(atom_structure))
    interval=formula._interval
    lower=interval[0]
    upper=interval[1]

    x_array = []
    y_array = []
    severity_array = []

    for element in result:
        x_array.append(element[1])
        y = float(element[0])
        #d is the distance from observed value to the nearest interval bound
        d=min(abs(y-lower),abs(y-upper))
        #sign=-1 if verdict value=0 and sign=1 if verdict is true
        sign=-1+2*(element[3])
        severity_array.append(sign*d)
        y_array.append(y)

    connection.close()
    return {"x": x_array, "observation": y_array, "severity" : severity_array}

def get_plot_data_between(dict):
    connection = get_connection()
    cursor = connection.cursor()

    calls_list = dict["calls"]
    binding_index = dict["binding"]
    atom_index = dict["atom"]
    points_list = dict["points"]

    query_string = """select o1.observed_value, o2.observed_value,
                             o1.observation_time, o2.observation_time,
                             verdict.verdict
                      from verdict inner join observation o1 on verdict.id==o1.verdict
                      inner join observation o2 where o1.verdict=o2.verdict
                      and o1.instrumentation_point<o2.instrumentation_point
                      and o1.instrumentation_point in %s and o2.instrumentation_point in %s
                      and o1.verdict in (select verdict.id from verdict inner join binding
                                         on verdict.binding == binding.id where verdict.function_call in %s and
                                         binding.binding_space_index=%s)
                      and o1.atom_index = %s and o2.atom_index = %s;""" % (
            list_to_sql_string(points_list), list_to_sql_string(points_list),
            list_to_sql_string(calls_list), binding_index, atom_index, atom_index)
    result = cursor.execute(query_string).fetchall()

    prop_hash = cursor.execute("""select distinct function_property_pair.property_hash from
    (((function_property_pair inner join function_call on function_property_pair.function==function_call.function)
    inner join verdict on function_call.id==verdict.function_call) inner join observation
       on observation.verdict==verdict.id) where observation.instrumentation_point=?""",
       [points_list[0]]).fetchone()[0]

    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    formula = pickle.loads(base64.b64decode(atom_structure))
    interval=formula._interval
    lower=interval[0]
    upper=interval[1]

    x_array = []
    y_array = []
    severity_array = []

    for element in result:
        x_array.append(element[2])
        time1 = element[1][12:-2]
        time2 = element[0][12:-2]
        y = abs((dateutil.parser.parse(time1) - dateutil.parser.parse(time2)).total_seconds())
        #y = float(json.loads(element[4])["time"])-float(json.loads(element[1])["time"])
        #d is the distance from observed value to the nearest interval bound
        d=min(abs(y-lower),abs(y-upper))
        #sign=-1 if verdict value=0 and sign=1 if verdict is true
        sign=-1+2*(element[4])
        severity_array.append(sign*d)
        y_array.append(y)

    connection.close()
    return {"x": x_array, "between-observation": y_array, "between-severity" : severity_array}


"""
Auxiliary functions for path reconstruction
"""

atoms_list = []
def property_to_atoms_list(prop):
    """
    Given a deserialised property, recurse down the formula structure and add atoms
    to the global variable atoms_list
    """
    global atoms_list
    if ((type(prop) is LogicalOr) or (type(prop) is LogicalAnd)):
        sub_formulas = prop.operands
        for sub_formula in sub_formulas:
            property_to_atoms_list(sub_formula)

    elif type(prop) is LogicalNot:
        property_to_atoms_list(prop.operand)

    else:
        atoms_list.append(prop)

    return

def list_to_sql_string(ids_list):
    """ Create a string which stores the list of ids as (1, 2, 3, 4)
     to be compatible with the sqlite query syntax: select * from ... where id in (1, 2, 3, 4)
     """
    ids="("
    for id in ids_list:
        if ids!="(":
            ids=ids+", "
        ids = ids + str(id)
    ids = ids + ")"
    return ids

def get_qualifier_subsequence(function_qualifier):
    """Given a fully qualified function name, iterate over it and find the file in which the function is defined (
    this is the entry in the qualifier chain before the one that causes an import error) """

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
        elif n == len(function_qualifier) - 1:
            tokens.append(function_qualifier[last_position:])

    return tokens

def get_scfg(func, location):
    if "-" in func[0:func.index(".")]:
        func = func[func.index("-")+1:]

    module = func[0:func.rindex(".")]
    func = func[func.rindex(".") + 1:]
    file_name = module.replace(".", "/") + ".py.inst"
    # extract asts from the code in the file
    code = "".join(open(os.path.join(location, file_name), "r").readlines())
    asts = ast.parse(code)
    qualifier_subsequence = get_qualifier_subsequence(func)
    func = func.replace(":", ".")
    function_name = func.split(".")
    # find the function definition
    actual_function_name = function_name[-1]
    hierarchy = function_name[:-1]
    current_step = asts.body
    # traverse sub structures
    for step in hierarchy:
        current_step = filter(lambda entry: (type(entry) is ast.ClassDef and entry.name == step), current_step)[0]
    # find the final function definition
    function_def = list(filter(lambda entry: (type(entry) is ast.FunctionDef and entry.name == actual_function_name),
                          current_step.body if type(current_step) is ast.ClassDef else current_step))[0]
    # construct the scfg of the code inside the function
    scfg = CFG()
    scfg.process_block(function_def.body)
    return scfg

def edges_from_condition_sequence(scfg, path_subchain, instrumentation_point_path_length):
    """
    Given a sequence of (deserialised) conditions in path_subchain and the final path length,
    reconstruct a path through the scfg, including loop multiplicity.
    If instrumentation_point_path_length = -1, we assume we're reconstructing a complete path through the SCFG.
    """
    #print("reconstruction with path subchain %s" % str(path_subchain))
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

            #TODO: need to handle parameters in condition sequences
            if path_subchain[condition_index] == "parameter":
                if curr._name_changed == ["conditional"]:
                    # add the vertex to the path, skip past the construct
                    # and increment the condition index
                    path.append(curr)
                    curr = curr.post_conditional_vertex
                    condition_index += 1
                    continue

            # we have to decide whether it's a loop or a conditional
            if curr._name_changed == ["conditional"]:
                #print("traversing conditional %s with condition %s" % (curr, path_subchain[condition_index]))
                # path_subchain[condition_index] is the index of the branch to follow if we're dealing with a conditional
                path.append(curr.edges[int(path_subchain[condition_index])])
                curr = curr.edges[int(path_subchain[condition_index])]._target_state
                condition_index += 1
            elif curr._name_changed == ["loop"]:
                #print("traversing loop %s with condition %s" % (curr, path_subchain[condition_index]))
                if path_subchain[condition_index] == "enter-loop":
                    #print("finding edge entering the loop")
                    # condition isn't a negation, so follow the edge leading into the loop
                    for edge in curr.edges:
                        #print(edge._condition)
                        if edge._condition == ["enter-loop"]:
                            #print("traversing edge with positive loop condition")
                            cumulative_conditions.append("for")
                            # follow this edge
                            curr = edge._target_state
                            path.append(edge)
                            break
                    # make sure the next branching point consumes the next condition in the chain
                    condition_index += 1
                else:
                    #print("finding edge skipping the loop")
                    # go straight past the loop
                    for edge in curr.edges:
                        if edge._condition == ["end-loop"]:
                            #print("traversing edge with negative loop condition")
                            cumulative_conditions.append(edge._condition)
                            # follow this edge
                            curr = edge._target_state
                            path.append(edge)
                            break
                    # make sure the next branching point consumes the next condition in the chain
                    condition_index += 1
            elif curr._name_changed == ["try-catch"]:
                #print("traversing try-catch")
                # for now assume that we immediately traverse the no-exception branch
                #print(curr)
                # search the outgoing edges for the edge leading to the main body
                for edge in curr.edges:
                    #print("testing edge with condition %s against cumulative condition %s" %\
                    #		(edge._condition, cumulative_conditions + [path_subchain[condition_index]]))
                    if edge._condition[-1] == "try-catch-main":
                        #print("traversing edge with condition %s" % edge._condition)
                        curr = edge._target_state
                        path.append(edge)
                        cumulative_conditions.append(edge._condition[-1])
                        break
                condition_index += 1
            else:
                # probably the branching point at the end of a loop - currently these aren't explicitly marked
                # the behaviour here with respect to consuming branching conditions will be a bit different
                if path_subchain[condition_index] == "enter-loop":
                    # go back to the start of the loop without consuming the condition
                    #print("going back around the loop from last instruction")
                    relevant_edge = list(filter(lambda edge : edge._condition == 'loop-jump', curr.edges))[0]
                    curr = relevant_edge._target_state
                    path.append(relevant_edge)
                else:
                    # go past the loop
                    #print(curr.edges)
                    #print("ending loop from last instruction")
                    relevant_edge = list(filter(lambda edge : edge._condition == 'post-loop', curr.edges))[0]
                    curr = relevant_edge._target_state
                    path.append(relevant_edge)
                    # consume the negative condition
                    condition_index += 1

            #print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
        elif curr._name_changed == ["post-conditional"]:
            #print("traversing post-conditional")
            # check the next vertex - if it's also a post-conditional, we move to that one but don't consume the condition
            # if the next vertex isn't a post-conditional, we consume the condition and move to it
            if curr.edges[0]._target_state._name_changed != ["post-conditional"]:
                # consume the condition
                condition_index += 1
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state
            #print("resulting state after conditional is %s" % curr)
            #print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
        elif curr._name_changed == ["post-loop"]:
            #print("traversing post-loop")
            # condition is consumed when branching at the end of the loop is detected, so no need to do it here
            #print("adding %s outgoing from %s to path" % (curr.edges[0], curr))
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state
            #print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
        elif curr._name_changed == ["post-try-catch"]:
            #print("traversing post-try-catch")
            if curr.edges[0]._target_state._name_changed != ["post-try-catch"]:
                # consume the condition
                condition_index += 1
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state
            #print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
        else:
            #print("no branching at %s" % curr)
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state
            #print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))

    #print("finishing path traversal with path length %i" % instrumentation_point_path_length)

    # traverse the remainder of the branch using the path length of the instrumentation point
    # that generated the observation we're looking at
    # print("starting remainder of traversal from vertex %s" % curr)
    if instrumentation_point_path_length != -1:
        # the length here needs to be changed depending on what the most recent construct the graph encountered was
        # or we need to move the vertex back one in the case that it advanced "too far".
        offset = -1 if curr._path_length == 1 else 0
        limit = (instrumentation_point_path_length + offset) if len(path_subchain) > 0 else instrumentation_point_path_length
        for i in range(limit):
            #path.append(curr)
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state
    else:
        # we're reconstructing a complete path through the SCFG, so go until we get to a final state
        while len(curr.edges) > 0:
            path.append(curr.edges[0])
            curr = curr.edges[0]._target_state

    #path.append(curr)

    return path


"""
list of changed repr methods follows - for Atoms and LogicalOr, And and Not
for each type of atom, it should display it similar to how it was given in the specification
if we want to build the HTML on the server side, set HTML_ON to true and the HTMLrepr functions will be
used, if not, __repr__ methods is used for representation
"""

StateValueInInterval.__repr__ = \
    lambda Atom: "%s(%s)._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueInOpenInterval.__repr__ = \
    lambda Atom: "%s(%s)._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueEqualTo.__repr__ = \
    lambda Atom: "%s(%s).equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueTypeEqualTo.__repr__ = \
    lambda Atom: "%s(%s).type().equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueEqualToMixed.__repr__ = \
    lambda Atom: "%s(%s).equals(%s(%s))" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthLessThanStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s(%s).length() < %s(%s).length()" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthInInterval.__repr__ = \
    lambda Atom: "%s(%s).length()._in(%s)" % (Atom._state, Atom._name, Atom._interval)

TransitionDurationInInterval.__repr__=\
    lambda Atom: "%s.duration()._in(%s)" % (Atom._transition, Atom._interval)

TransitionDurationLessThanTransitionDurationMixed.__repr__=\
    lambda Atom: "%s.duration() < %s.duration()" % (Atom._lhs, Atom._rhs)

TransitionDurationLessThanStateValueMixed.__repr__ = \
    lambda Atom: "%s.duration() < %s(%s)" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s.duration() < %s(%s).length()" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TimeBetweenInInterval.__repr__ = \
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, Atom._interval)

TimeBetweenInOpenInterval.__repr__ = \
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, str(Atom._interval))

LogicalAnd.__repr__= \
    lambda object: ('land(%s' % (object.operands[0])) + (', %s'%str for str in object.operands[1:]) + ')'

LogicalOr.__repr__= \
    lambda object: ('lor(%s' % (object.operands[0])) + (', %s'%str for str in object.operands[1:]) + ')'

LogicalNot.__repr__ = \
    lambda object: 'lnot(%s)' % object.operand

"""HTML repr functions"""

StateValueInInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

StateValueInOpenInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

StateValueEqualTo.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>.equals(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._value)

StateValueTypeEqualTo.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>.type().equals(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._value)

StateValueEqualToMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>.equals(
        <span class="subatom" subatom-index="1">%s(%s)</span>)
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthLessThanStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>.length() <
        <span class="subatom" subatom-index="1">%s(%s)</span>.length()
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthInInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s(%s)</span>.length()._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

TransitionDurationInInterval.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._transition, Atom._interval)

TransitionDurationLessThanTransitionDurationMixed.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="duration"><span class="subatom" subatom-index="1">%s</span>.duration()</span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._rhs)

TransitionDurationLessThanStateValueMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="subatom" subatom-index="1">%s(%s) </span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="subatom" subatom-index="1">%s(%s)</span>.length()
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._rhs, Atom._rhs_name)

TimeBetweenInInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">timeBetween(
        <span class="subatom" subatom-index="0">%s</span>,
        <span class="subatom" subatom-index="1">%s</span>)._in(%s)
        </span> """ % (atoms_list.index(Atom), Atom._lhs, Atom._rhs, Atom._interval)

TimeBetweenInOpenInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">timeBetween(
        <span class="subatom" subatom-index="0">%s</span>,
        <span class="subatom" subatom-index="1">%s</span>)._in(%s)
        </span> """ % (atoms_list.index(Atom), Atom._lhs, Atom._rhs, str(Atom._interval))

LogicalAnd.HTMLrepr= \
    lambda object: ('land(%s' % (object.operands[0].HTMLrepr())) + (', %s'%str.HTMLrepr() for str in object.operands[1:]) + ')'

LogicalOr.HTMLrepr= \
    lambda object: ('lor(%s' % (object.operands[0].HTMLrepr())) + (', %s'%str.HTMLrepr() for str in object.operands[1:]) + ')'

LogicalNot.HTMLrepr = \
    lambda object: 'lnot(%s)' % object.operand.HTMLrepr()


"""
we need to display states also similar to how they are defined in the specification
new function because other __repr__ is also needed
TODO: other possible states ??
"""

StaticState.my_repr_function = \
    lambda object: "%s = changes('%s')" % (object._bind_variable_name, object._name_changed)

StaticTransition.my_repr_function = \
    lambda object: "%s = calls('%s')" % (object._bind_variable_name, object._operates_on)
