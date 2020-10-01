"""
Module to provide functions for the web analysis tool to use.

"""
from .utils import get_connection
import json
import dateutil.parser
from dateutil.parser import isoparse
import pickle
import base64
from VyPR.monitor_synthesis.formula_tree import *
from VyPR.QueryBuilding.formula_building import *
from VyPR.SCFG.construction import *
from VyPR.SCFG.parse_tree import ParseTree
import app
import ast
import os
import hashlib
import datetime
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure, locator_params


def list_calls_from_id(function_id, tests = None):
    """
    Given a function id (which implicitly also fixes a property), list the calls found.
    The list of test IDs is optional, in case it is given, list only the calls that happen
    during the tests.
    """
    connection = get_connection()
    cursor = connection.cursor()
    if tests == None:
        function_calls = cursor.execute("select * from function_call where function = ?", [function_id]).fetchall()
    else:
        names = []
        for name in tests:
            names.append('"%s"' %name)
        function_calls = cursor.execute("""select * from function_call where function=?
            and id in (select function_call.id from function_call inner join test_data
                        where function_call.time_of_call>=test_data.start_time
                        and function_call.end_time_of_call<=test_data.end_time
                        and test_data.test_name in %s);"""%list_to_sql_string(names), [function_id]).fetchall()

    # perform any processing on each function call that we need
    modified_calls = []
    for function_call in function_calls:
        new_call = list(function_call)

        # append the time taken
        new_call.append(
            (dateutil.parser.parse(new_call[3]) - dateutil.parser.parse(new_call[2])).total_seconds()
        )
        # format the timestamps
        new_call[2] = dateutil.parser.parse(new_call[2]).strftime("%d/%m/%Y %H:%M:%S")
        new_call[3] = dateutil.parser.parse(new_call[3]).strftime("%d/%m/%Y %H:%M:%S")

        # append verdict data
        verdicts = map(
            lambda row: row[0],
            cursor.execute(
                "select verdict from verdict where function_call = ?",
                [function_call[0]]
            ).fetchall()
        )
        # take the numerical product of verdicts
        overall_verdict = 1
        for verdict in verdicts:
            overall_verdict *= verdict
        new_call.append(overall_verdict)

        # if tests were given, determine during which test this call took place
        if tests:
            test_result = cursor.execute("""select test_result from test_data
                where start_time < ? and end_time > ?""", [function_call[2], function_call[3]]).fetchone()[0]
            new_call.append(test_result)

        modified_calls.append(new_call)
    return modified_calls


def list_calls_in_interval(start, end, function_id, test_names = None):
    """start and end are strings in dd/mm/yyyy hh:mm:ss format"""
    connection = get_connection()
    cursor = connection.cursor()

    start_timestamp = dateutil.parser.parse(start.replace("%20"," ")).strftime("%Y-%m-%dT%H:%M:%S")
    end_timestamp = dateutil.parser.parse(end.replace("%20", " ")).strftime("%Y-%m-%dT%H:%M:%S")

    if test_names == None:
        function_calls = cursor.execute("""select id from function_call where time_of_call>=?
        and end_time_of_call <= ? and function=?""", [start_timestamp, end_timestamp, function_id]).fetchall()
    else:
        names = []
        for name in test_names:
            names.append('"%s"' %name)
        function_calls = cursor.execute(""" select function_call.id from
            function_call inner join test_data where
            function_call.time_of_call>=test_data.start_time
            and function_call.end_time_of_call<=test_data.end_time
            and function_call.time_of_call>=? and function_call.end_time_of_call <= ?
            and function=? and test_data.test_name in %s; """%list_to_sql_string(names),
            [start_timestamp, end_timestamp, function_id]).fetchall()


    connection.close()
    return function_calls


def web_list_tests():
    """
    Return a list of all tests in the database - possibly empty
    """

    connection = get_connection()
    cursor = connection.cursor()

    query_string = "select distinct test_name from test_data"

    try:
        tests = cursor.execute(query_string).fetchall()
    except:
        tests = []

    connection.close()
    return tests


def web_list_functions(tests = None):
    """
    Return a list of all functions found. Adding an optional tests parameter
    - if a list of test IDs is passed, the list of functions will be filtered so that only those
      monitored during the selected tests get listed
    """

    print("listing functions")

    connection = get_connection()
    cursor = connection.cursor()

    if tests==None:
        functions = cursor.execute(
        """select function.id, function.fully_qualified_name, property.hash, property.serialised_structure
            from (function inner join function_property_pair on function.id==function_property_pair.function)
            inner join property on function_property_pair.property_hash==property.hash""").fetchall()
    else:
        names = []
        for name in tests["names"]:
            names.append('"%s"' %name)
        ids = cursor.execute(
        """select distinct function_call.function from test_data inner join function_call
            where function_call.time_of_call>=test_data.start_time
            and function_call.end_time_of_call<=test_data.end_time
            and test_data.test_name in %s;""" % list_to_sql_string(names)).fetchall()
        ids_new = []
        for id in ids:
            ids_new.append(id[0])
        functions = cursor.execute(
        """select function.id, function.fully_qualified_name, property.hash, property.serialised_structure
            from (function inner join function_property_pair on function.id==function_property_pair.function)
            inner join property on function_property_pair.property_hash==property.hash
            where function.id in %s;"""%list_to_sql_string(ids_new)).fetchall()

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
            path_rest = machine_rest[0].split(".")
            machine = [""]
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
        # arithmetic stack representation doesn't work on properties obtained this way

        # if property contains only one atom, find it and get the serialised structure from there instead
        atom_structure = cursor.execute("""select atom.serialised_structure
            from atom inner join property on atom.property_hash==property.hash
            where property.hash = ?;""", [function[2]]).fetchall()
        if len(atom_structure) == 1:
            formula = pickle.loads(base64.b64decode(atom_structure[0][0]))
            prop = formula
        # TODO else

        # bind_var was decoded in the first step of the loop

        global atoms_list
        atoms_list = []
        property_to_atoms_list(prop)


        #return specification as dict with data based on which the front end will build the HTML
        HTML_ON = False

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
            print(prop.operands[0].HTMLrepr())
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
        error_dict = {"error" : "Please provide the monitored service source code location (--path)."}
        return error_dict

    if "-" in func[0:func.index(".")]:
        func = func[func.index("-")+1:]

    module = func[0:func.rindex(".")]
    func = func[func.rindex(".") + 1:]
    file_name = module.replace(".", "/") + ".py.inst"
    # extract asts from the code in the file
    try:
        code = "".join(open(os.path.join(location, file_name), "r").readlines())
    except:
        error_dict = {"error" : "Monitored service source code not found at given location."}
        return error_dict
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
    end = function_def.body[-1].lineno
    #in case last element spans over multiple lines, find the last line number
    for node in ast.walk(function_def.body[-1]):
        try:
            node_line = node.lineno
            if node_line > end:
                end = node_line
        except:
            pass
    end = end - 1
    lines = code.split('\n')


    #take the section of code between the line numbers - this is the source code
    #of the function of interest without the rest of the code
    f_code = lines[start:(end+1)]

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


def get_calls_data(ids_list, property_hash):
    """
    Given a list of function call IDs, using path condition sequence,
     reconstruct the path taken to an instrumentation point

    """
    #print(ids_list)
    connection = get_connection()
    cursor = connection.cursor()

    ids = list_to_sql_string(ids_list)

    query_string = "select id, function, time_of_call, end_time_of_call, trans, path_condition_id_sequence " \
                   "from function_call where id in %s;" % ids
    calls = cursor.execute(query_string).fetchall()
    #print(calls)

    # check if the monitored service path was given as an argument
    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please pass the monitored service path as an argument (--path)"}
        return error_dict

    # get the scfg of the function called by these calls and get all their path_condition_id_sequences
    # but without duplicate instances of sequences - store them as keys in dictionary 'sequences'
    # the corresponding value is a list of the IDs of the calls that generated the sequence (key)
    function = cursor.execute("select fully_qualified_name from function where id = ?", [calls[0][1]]
    ).fetchone()
    func = function[0]
    scfg = get_scfg(func, location)
    sequences = {}
    inst_point_ids = set()
    lines = set()

    # get the set of binding IDs for the given function
    bindings = map(
        lambda row : row[0],
        cursor.execute(
            "select id from binding where function = ? and property_hash = ?",
            [calls[0][1], property_hash]
        ).fetchall()
    )

    print("bindings %s" % bindings)

    for call in calls:
        seq = call[5]  # get the list of path condition ids
        if seq not in sequences.keys():
            sequences[seq] = [call[0]]
        else:
            sequences[seq].append(call[0])

    for seq in sequences:
        # if there are more calls that generated the sequence, take the first one
        call_id = sequences[seq][0]
        print("call id %i" % call_id)
        # get the list of path conditions defined by the ids above
        subchain = []
        for condition in json.loads(seq):
            query_string = "select serialised_condition from path_condition_structure where id = %s;" % condition
            condition_string = cursor.execute(query_string).fetchone()[0]
            subchain.append(condition_string)
        print(subchain)

        # get observations generated during this function call that are relevant to the property
        observations = cursor.execute(
            """select observation.id, observation.instrumentation_point,
            observation.previous_condition_offset from
            (observation inner join verdict on observation.verdict == verdict.id)
            where verdict.function_call = ? and verdict.binding in %s""" % list_to_sql_string(bindings),
            [call_id]
        ).fetchall()

        print(observations)

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

    # in addition to lines at which instrumenation points are, we also need to know
    # which lines are of interest due to being refered to by the quantifiers
    # as they are not paired with atoms, we store them within the corresponding binding,
    # but set the atom and subatom indices to -1
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

    print("%s -> inst point %s" % (prop_hash, inst_point_id))

    print(prop_hash)
    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    atom_deserialised = pickle.loads(base64.b64decode(atom_structure))

    connection.close()

    if type(atom_deserialised) in [StateValueEqualToMixed, StateValueLessThanStateValueMixed,
        StateValueLessThanEqualStateValueMixed, StateValueLengthLessThanStateValueLengthMixed,
        StateValueLengthLessThanEqualStateValueLengthMixed,
        TransitionDurationLessThanTransitionDurationMixed,
        TransitionDurationLessThanEqualTransitionDurationMixed,
        TransitionDurationLessThanStateValueMixed, TransitionDurationLessThanEqualStateValueMixed,
        TransitionDurationLessThanStateValueLengthMixed, TransitionDurationLessThanEqualStateValueLengthMixed]:
        return 'mixed'

    elif type(atom_deserialised) in [TimeBetweenInInterval, TimeBetweenInOpenInterval]:
        return 'timeBetween'

    else:
        return 'simple'


def write_plot(plot_hash):
    """
    Given a plot hash, get the plot data, generate a plot, write it to a file and return the file name.
    """
    connection = get_connection()
    cursor = connection.cursor()

    filename = "%s.pdf" % plot_hash

    result = cursor.execute("select description, data from plot where hash = ?", [plot_hash]).fetchone()
    plot_description = json.loads(result[0])
    plot_data = json.loads(result[1])
    plot_type = plot_description["type"]

    xs = map(lambda x : x.split("T")[1], plot_data["x"])
    ys = plot_data[plot_type]

    figure(figsize=(20, 6))
    plt.bar(xs, ys, align="center", ecolor="black")
    plt.xlabel("TIMESTAMP")
    plt.ylabel(plot_type.upper())
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig("generated_plots/%s" % filename)

    return filename


def get_plot(cursor, plot_dict):
    """
    Check whether a plot already exists given its dictionary.
    """
    plot_dict_json = json.dumps(plot_dict)
    results = cursor.execute("select * from plot where description = ?", [plot_dict_json]).fetchall()
    print("existence results")
    print(results)
    return results


def store_plot(cursor, plot_hash, plot_description, plot_data):
    """
    Store a new plot so it can be retreived later without recomputation.
    """
    cursor.execute(
        "insert into plot values(?, ?, ?, ?)",
        [
            plot_hash, json.dumps(plot_description), json.dumps(plot_data), datetime.datetime.now()
        ]
    )


def get_plot_data_from_hash(plot_hash):
    """
    Given a uniquely identifying plot hash, get its data
    """
    connection = get_connection()
    cursor = connection.cursor()
    plot_data = cursor.execute("select hash, description, data from plot where hash = ?", [plot_hash]).fetchone()
    return {
        "hash" : plot_data[0],
        "description" : json.loads(plot_data[1]),
        "data" : json.loads(plot_data[2])
    }


def get_plot_data_simple(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the plot already exists
    plot_results = get_plot(cursor, dict)
    if len(plot_results) > 0:
        print("existing plot found with hash %s" % plot_results[0][0])
        print(dict)
        # the plot exists, so use the precomputed data
        final_dictionary = {
            "plot_hash" : plot_results[0][0],
            "plot_data" : json.loads(plot_results[0][2])
        }
        return final_dictionary
    else:
        print("no existing plot found")
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
        try:
            interval = formula._interval
            lower = interval[0]
            upper = interval[1]
        except:
            #right now, for simple atoms are either observation in interval or obs = value
            #hence, inequalities are not covered here
            value = formula._value
            lower = value
            upper = value

        x_array = []
        y_array = []
        severity_array = []

        for element in result:
            x_array.append(element[1])
            y = float(element[0])
            # d is the distance from observed value to the nearest interval bound
            # if condition is value = x then interval was set to [x,x]
            # intervals contain numerical values, but equalities might not
            try:
                d = min(abs(y-lower),abs(y-upper))
            except:
                # set distance to zero if the equality is satisfied, otherwise distance is 1
                # might want to change this
                d = (y != lower)
            #sign=-1 if verdict value=0 and sign=1 if verdict is true
            sign = -1 + 2 * (element[3])
            severity_array.append(sign*d)
            y_array.append(y)

        # build the plot data dictionary
        plot_data = {"x": x_array, "observation": y_array, "severity": severity_array}
        # generate a hash of the plot data
        plot_hash = hashlib.sha1()
        plot_hash.update(json.dumps(plot_data))
        plot_hash.update(json.dumps(dict))
        plot_hash = plot_hash.hexdigest()
        # store the plot
        store_plot(cursor, plot_hash, dict, plot_data)
        connection.commit()

        connection.close()

        return {
            "plot_hash" : plot_hash,
            "plot_data" : plot_data
        }


def get_plot_data_between(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the plot already exists
    plot_results = get_plot(cursor, dict)
    if len(plot_results) > 0:
        print("existing plot found with hash %s" % plot_results[0][0])
        # the plot exists, so use the precomputed data
        final_dictionary = {
            "plot_hash": plot_results[0][0],
            "plot_data": json.loads(plot_results[0][2])
        }
        return final_dictionary
    else:

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

            #d is the distance from observed value to the nearest interval bound
            d=min(abs(y-lower),abs(y-upper))
            #sign=-1 if verdict value=0 and sign=1 if verdict is true
            sign=-1+2*(element[4])

            severity_array.append(sign*d)
            y_array.append(y)

        # build the final plot data
        plot_data = {"x": x_array, "between-observation": y_array, "between-severity" : severity_array}
        # generate a hash of the plot data
        plot_hash = hashlib.sha1()
        plot_hash.update(json.dumps(plot_data))
        plot_hash.update(json.dumps(dict))
        plot_hash = plot_hash.hexdigest()
        # store the plot
        store_plot(cursor, plot_hash, dict, plot_data)
        connection.commit()

        connection.close()

        return {
            "plot_hash": plot_hash,
            "plot_data": plot_data
        }


def get_plot_data_mixed(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the plot already exists
    plot_results = get_plot(cursor, dict)
    if len(plot_results) > 0:
        print("existing plot found with hash %s" % plot_results[0][0])
        # the plot exists, so use the precomputed data
        final_dictionary = {
            "plot_hash": plot_results[0][0],
            "plot_data": json.loads(plot_results[0][2])
        }
        return final_dictionary
    else:

        calls_list = dict["calls"]
        binding_index = dict["binding"]
        atom_index = dict["atom"]
        points_list = dict["points"]

        query_string = """select o1.observed_value, o2.observed_value,
                                 o1.observation_time, o2.observation_time,
                                 verdict.verdict, o1.sub_index
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

        x1_array = []
        y1_array = []
        x2_array = []
        y2_array = []
        severity_array = []

        for element in result:
            if element[5] == 0:
                dict0 = ast.literal_eval(element[0])
                dict1 = ast.literal_eval(element[1])
                x1_array.append(element[2])
                x2_array.append(element[3])
            else:
                dict0 = ast.literal_eval(element[1])
                dict1 = ast.literal_eval(element[0])
                x1_array.append(element[3])
                x2_array.append(element[2])

            for key in dict0:
                elem0 = dict0[key]
            for key in dict1:
                elem1 = dict1[key]

            y1_array.append(elem0)
            y2_array.append(elem1)

            sign = -1 + 2*element[4]
            try:
                stack_left = formula._lhs._arithmetic_stack
            except:
                stack_left = []
            try:
                stack_right = formula._rhs._arithmetic_stack
            except:
                stack_right = []

            d = abs(apply_arithmetic_stack(stack_right, elem1) -
                    apply_arithmetic_stack(stack_left, elem0))
            severity_array.append(sign*d)

        # build the final plot data
        plot_data = {"x1" : x1_array, "mixed-observation-1" : y1_array,
                     "x2" : x2_array, "mixed-observation-2" : y2_array,
                     "mixed-severity" : severity_array}
        # generate a hash of the plot data
        plot_hash = hashlib.sha1()
        plot_hash.update(json.dumps(plot_data))
        plot_hash.update(json.dumps(dict))
        plot_hash = plot_hash.hexdigest()
        # store the plot
        store_plot(cursor, plot_hash, dict, plot_data)
        connection.commit()

        connection.close()

        return {
            "plot_hash": plot_hash,
            "plot_data": plot_data
        }


def get_path_data_between(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the path data was already calculated
    path_results = get_plot(cursor, dict)
    if len(path_results) > 0:
        print("existing paths found with hash %s" % path_results[0][0])
        # the plot exists, so use the precomputed data
        final_dictionary = json.loads(path_results[0][2])
        final_dictionary["path_hash"] = path_results[0][0]
        return final_dictionary

    calls_list = dict["calls"]
    binding_index = dict["binding"]
    atom_index = dict["atom"]
    points_list = dict["points"]

    # points_list contains a pair of points - we need the length of path up to each one
    lengths = cursor.execute("""select reaching_path_length from instrumentation_point
        where id in %s order by id"""%list_to_sql_string(points_list)).fetchall()
    path_length_lhs = lengths[0][0]
    path_length_rhs = lengths[1][0]

    query_string = """select o1.observed_value, o2.observed_value,
                             o1.observation_time, o2.observation_time,
                             o1.previous_condition_offset, o2.previous_condition_offset,
                             verdict.verdict, function_call.path_condition_id_sequence
                      from ((function_call inner join verdict on function_call.id == verdict.function_call)
                      inner join observation o1 on verdict.id==o1.verdict
                      inner join observation o2) where o1.verdict=o2.verdict
                      and o1.instrumentation_point<o2.instrumentation_point
                      and o1.instrumentation_point in %s and o2.instrumentation_point in %s
                      and o1.verdict in (select verdict.id from verdict inner join binding
                                         on verdict.binding == binding.id where verdict.function_call in %s and
                                         binding.binding_space_index=%s)
                      and o1.atom_index = %s and o2.atom_index = %s;""" % (
            list_to_sql_string(points_list), list_to_sql_string(points_list),
            list_to_sql_string(calls_list), binding_index, atom_index, atom_index)
    result = cursor.execute(query_string).fetchall()

    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please pass the monitored service path as an argument (--path)"}
        return error_dict

    # get the scfg of the function called by these calls
    function = cursor.execute("""select function.fully_qualified_name from function inner join
        function_call on function.id == function_call.function where function_call.id = ?""",
        [calls_list[0]]).fetchone()
    func = function[0]
    scfg = get_scfg(func, location)
    grammar = scfg.derive_grammar()

    # get the atom from the structure in property to determine the interval
    prop_hash = cursor.execute("""select distinct function_property_pair.property_hash from
        (function_property_pair inner join function_call
            on function_property_pair.function==function_call.function)
        where function_call.id = ?""", [calls_list[0]]).fetchone()[0]

    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    formula = pickle.loads(base64.b64decode(atom_structure))
    interval=formula._interval
    lower=interval[0]
    upper=interval[1]

    parse_trees_obs_value_pairs = []

    for element in result:
        subchain = []
        for condition in json.loads(element[7]):
            query_string = "select serialised_condition from path_condition_structure where id = %s;" % condition
            condition_string = cursor.execute(query_string).fetchone()[0]
            subchain.append(condition_string)

        path_condition_list_lhs = subchain[1:(element[4]+1)]
        path_condition_list_rhs = subchain[1:(element[5]+1)]
        lhs_path = edges_from_condition_sequence(scfg, path_condition_list_lhs, path_length_lhs)
        rhs_path = edges_from_condition_sequence(scfg, path_condition_list_rhs, path_length_rhs)
        if len(lhs_path) <= len(rhs_path):
            path_difference = rhs_path[len(lhs_path):]
        else:
            path_difference = lhs_path[len(rhs_path):]
        parse_tree = ParseTree(path_difference, grammar, path_difference[0]._source_state)
        lhs_time = isoparse(ast.literal_eval(element[0])["time"])
        rhs_time = isoparse(ast.literal_eval(element[1])["time"])
        time_taken = (rhs_time - lhs_time).total_seconds()
        #d is the distance from observed value to the nearest interval bound
        d=min(abs(time_taken-lower),abs(time_taken-upper))
        #sign=-1 if verdict value=0 and sign=1 if verdict is true
        sign=-1+2*(element[6])

        parse_trees_obs_value_pairs.append((parse_tree, time_taken, sign*d, element[2]))

    parse_trees, times, severities, x_axis = zip(*parse_trees_obs_value_pairs)

    intersection = parse_trees[0].intersect(parse_trees[1:])

    main_path = intersection.read_leaves()
    main_lines = []
    parameter_lines = []
    for element in main_path:
        if type(element) is CFGEdge:
            try:
                line_number = element._instruction.lineno
                main_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    main_lines.append(line_number)
                except:
                    pass
        else:

            try:
                line_number = element._instruction.lineno
                parameter_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    parameter_lines.append(line_number)
                except:
                    pass

    path_parameters = []
    intersection.get_parameter_paths(intersection._root_vertex, [], path_parameters)

    parameter_value_indices_to_times = {}
    parameter_value_indices_to_severities = {}
    parameter_value_indices_to_x_axis = {}
    subpaths = []

    if len(path_parameters) > 0:

        n_of_trees = len(parse_trees)
        for (n, parse_tree) in enumerate(parse_trees):
          subtree = parse_tree.get_parameter_subtree(path_parameters[0])
          subpath = subtree.read_leaves()
          if subpath in subpaths:
            subpath_index = subpaths.index(subpath)
          else:
            subpaths.append(subpath)
            subpath_index = len(subpaths)-1
          if subpath_index not in parameter_value_indices_to_times:
            parameter_value_indices_to_times[subpath_index] = [times[n]]
            parameter_value_indices_to_severities[subpath_index] = [severities[n]]
            parameter_value_indices_to_x_axis[subpath_index] = [x_axis[n]]
          else:
            parameter_value_indices_to_times[subpath_index].append(times[n])
            parameter_value_indices_to_severities[subpath_index].append(severities[n])
            parameter_value_indices_to_x_axis[subpath_index].append(x_axis[n])

        lines_by_subpaths = []

        for (i, subpath) in enumerate(subpaths):
            lines = []
            for element in subpath:
                try:
                    line_number = element._instruction.lineno
                    lines.append(line_number)
                except:
                    try:
                        line_number = element._instruction._structure_obj.lineno
                        lines.append(line_number)
                    except:
                        pass

                # fill in gaps in lines
                final_lines = []
                for n in range(len(lines)-1):
                    final_lines += [m for m in range(lines[n], lines[n+1]+1)]

            if len(lines) == 1: final_lines = lines
            lines_by_subpaths.append({"lines": final_lines,
                                      "observations": parameter_value_indices_to_times[i],
                                      "severities": parameter_value_indices_to_severities[i],
                                      "x": parameter_value_indices_to_x_axis[i]})
    else:

        lines_by_subpaths = []

    return_data = {
        "parameter_values": lines_by_subpaths,
        "main_lines": main_lines,
        "parameters": parameter_lines
    }

    # generate a hash of the data
    path_hash = hashlib.sha1()
    path_hash.update(json.dumps(return_data))
    path_hash.update(json.dumps(dict))
    path_hash = path_hash.hexdigest()
    # store the plot
    store_plot(cursor, path_hash, dict, return_data)
    connection.commit()

    connection.close()
    return_data["path_hash"] = path_hash
    return return_data


def get_path_data_simple(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the path data was already calculated
    path_results = get_plot(cursor, dict)
    if len(path_results) > 0:
        print("existing paths found with hash %s" % path_results[0][0])
        # the plot exists, so use the precomputed data
        final_dictionary = json.loads(path_results[0][2])
        final_dictionary["path_hash"] = path_results[0][0]
        return final_dictionary

    calls_list = dict["calls"]
    binding_index = dict["binding"]
    atom_index = dict["atom"]
    points_list = dict["points"]
    # all calls belong to the same function - find its ID
    function_id = cursor.execute("""select function.id from function inner join
        function_call on function.id == function_call.function where function_call.id = ?""",
        [calls_list[0]]).fetchone()[0]

    # inst point should be unique - in case it's not, takes one
    path_length = cursor.execute("""select reaching_path_length from instrumentation_point
        where id in %s"""%list_to_sql_string(points_list)).fetchone()[0]

    query_string = """select observation.observed_value, observation.previous_condition_offset,
                        verdict.verdict, function_call.path_condition_id_sequence,
                        observation.observation_time
                      from (observation inner join verdict on observation.verdict == verdict.id)
                        inner join function_call on verdict.function_call==function_call.id
                      where observation.instrumentation_point in %s and observation.atom_index=%s
                        and function_call.id in %s and verdict.binding = (select id
                        from binding where function=%s and binding_space_index=%s) """ % (
            list_to_sql_string(points_list), atom_index, list_to_sql_string(calls_list),
            function_id, binding_index)
    result = cursor.execute(query_string).fetchall()

    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please pass the monitored service path as an argument (--path)"}
        return error_dict

    # get the scfg of the function called by these calls
    function = cursor.execute("select fully_qualified_name from function where id = ?",
        [function_id]).fetchone()
    func = function[0]
    scfg = get_scfg(func, location)
    grammar = scfg.derive_grammar()

    # get the atom from the structure in property to determine the interval
    prop_hash = cursor.execute("""select distinct property_hash from function_property_pair
        where function = ?""", [function_id]).fetchone()[0]

    # in order to determine the verdict severity, we need the condition set by the specification
    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    formula = pickle.loads(base64.b64decode(atom_structure))
    try:
        # in case the formula requires the value to be in interval
        interval = formula._interval
        lower = interval[0]
        upper = interval[1]
    except:
        # in case the formula sets an equality
        value = formula._value
        lower = value
        upper = value

    parse_trees_obs_value_pairs = []

    for element in result:
        subchain = []
        for condition in json.loads(element[3]):
            query_string = "select serialised_condition from path_condition_structure where id = %s;" % condition
            condition_string = cursor.execute(query_string).fetchone()[0]
            subchain.append(condition_string)

        path_condition_list = subchain[1:(element[1]+1)]
        path = edges_from_condition_sequence(scfg, path_condition_list, path_length)

        parse_tree = ParseTree(path, grammar, path[0]._source_state)
        observed_value = json.loads(element[0])
        #d is the distance from observed value to the nearest interval bound
        # interval being [x, x] if condition is "observed_value = x"
        d=min(abs(observed_value-lower),abs(observed_value-upper))
        #sign=-1 if verdict value=0 and sign=1 if verdict is true
        sign=-1+2*(element[2])

        parse_trees_obs_value_pairs.append((parse_tree, observed_value, sign*d, element[4]))

    parse_trees, times, severities, x_axis = zip(*parse_trees_obs_value_pairs)

    intersection = parse_trees[0].intersect(parse_trees[1:])

    main_path = intersection.read_leaves()
    main_lines = []
    parameter_lines = []
    for element in main_path:
        if type(element) is CFGEdge:
            try:
                line_number = element._instruction.lineno
                main_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    main_lines.append(line_number)
                except:
                    pass
        else:

            try:
                line_number = element._instruction.lineno
                parameter_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    parameter_lines.append(line_number)
                except:
                    pass

    path_parameters = []
    intersection.get_parameter_paths(intersection._root_vertex, [], path_parameters)

    parameter_value_indices_to_times = {}
    parameter_value_indices_to_severities = {}
    parameter_value_indices_to_x_axis = {}
    subpaths = []

    if len(path_parameters) > 0:

        n_of_trees = len(parse_trees)
        for (n, parse_tree) in enumerate(parse_trees):
          subtree = parse_tree.get_parameter_subtree(path_parameters[0])
          subpath = subtree.read_leaves()
          if subpath in subpaths:
            subpath_index = subpaths.index(subpath)
          else:
            subpaths.append(subpath)
            subpath_index = len(subpaths)-1
          if subpath_index not in parameter_value_indices_to_times:
            parameter_value_indices_to_times[subpath_index] = [times[n]]
            parameter_value_indices_to_severities[subpath_index] = [severities[n]]
            parameter_value_indices_to_x_axis[subpath_index] = [x_axis[n]]
          else:
            parameter_value_indices_to_times[subpath_index].append(times[n])
            parameter_value_indices_to_severities[subpath_index].append(severities[n])
            parameter_value_indices_to_x_axis[subpath_index].append(x_axis[n])

        lines_by_subpaths = []

        for (i, subpath) in enumerate(subpaths):
            lines = []
            for element in subpath:
                try:
                    line_number = element._instruction.lineno
                    lines.append(line_number)
                except:
                    try:
                        line_number = element._instruction._structure_obj.lineno
                        lines.append(line_number)
                    except:
                        pass

                # fill in gaps in lines
                final_lines = []
                for n in range(len(lines)-1):
                    final_lines += [m for m in range(lines[n], lines[n+1]+1)]

            if len(lines) == 1: final_lines = lines
            lines_by_subpaths.append({"lines": final_lines,
                                      "observations": parameter_value_indices_to_times[i],
                                      "severities": parameter_value_indices_to_severities[i],
                                      "x": parameter_value_indices_to_x_axis[i]})
    else:

        lines_by_subpaths = []

    return_data = {
        "parameter_values": lines_by_subpaths,
        "main_lines": main_lines,
        "parameters": parameter_lines
    }

    # generate a hash of the data
    path_hash = hashlib.sha1()
    path_hash.update(json.dumps(return_data))
    path_hash.update(json.dumps(dict))
    path_hash = path_hash.hexdigest()
    # store the plot
    store_plot(cursor, path_hash, dict, return_data)
    connection.commit()

    connection.close()
    return_data["path_hash"] = path_hash
    return return_data


def get_path_data_mixed(dict):
    connection = get_connection()
    cursor = connection.cursor()

    # first, check if the path data was already calculated
    path_results = get_plot(cursor, dict)
    if len(path_results) > 0:
        print("existing paths found with hash %s" % path_results[0][0])
        # the plot exists, so use the precomputed data
        final_dictionary = json.loads(path_results[0][2])
        final_dictionary["path_hash"] = path_results[0][0]
        return final_dictionary

    calls_list = dict["calls"]
    binding_index = dict["binding"]
    atom_index = dict["atom"]
    points_list = dict["points"]

    lengths = cursor.execute("""select reaching_path_length from instrumentation_point
        where id in %s order by id"""%list_to_sql_string(points_list)).fetchall()
    path_length_lhs = lengths[0][0]
    path_length_rhs = lengths[1][0]

    query_string = """select o1.observed_value, o2.observed_value,
                             o1.observation_time, o2.observation_time,
                             o1.previous_condition_offset, o2.previous_condition_offset,
                             verdict.verdict, function_call.path_condition_id_sequence
                      from ((function_call inner join verdict on function_call.id == verdict.function_call)
                      inner join observation o1 on verdict.id==o1.verdict
                      inner join observation o2) where o1.verdict=o2.verdict
                      and o1.instrumentation_point<o2.instrumentation_point
                      and o1.instrumentation_point in %s and o2.instrumentation_point in %s
                      and o1.verdict in (select verdict.id from verdict inner join binding
                                         on verdict.binding == binding.id where verdict.function_call in %s and
                                         binding.binding_space_index=%s)
                      and o1.atom_index = %s and o2.atom_index = %s;""" % (
            list_to_sql_string(points_list), list_to_sql_string(points_list),
            list_to_sql_string(calls_list), binding_index, atom_index, atom_index)
    result = cursor.execute(query_string).fetchall()

    location = app.monitored_service_path
    if (location==None):
        error_dict = {"error" : "Please pass the monitored service path as an argument (--path)"}
        return error_dict

    # get the scfg of the function called by these calls
    function = cursor.execute("""select function.fully_qualified_name from function inner join
        function_call on function.id == function_call.function where function_call.id = ?""",
        [calls_list[0]]).fetchone()
    func = function[0]
    scfg = get_scfg(func, location)
    grammar = scfg.derive_grammar()

    # get the atom from the structure in property to determine the interval
    prop_hash = cursor.execute("""select distinct function_property_pair.property_hash from
        (function_property_pair inner join function_call
            on function_property_pair.function==function_call.function)
        where function_call.id = ?""", [calls_list[0]]).fetchone()[0]

    atom_structure = cursor.execute("""select serialised_structure from atom where index_in_atoms=?
        and property_hash=?""", [atom_index, prop_hash]).fetchone()[0]
    formula = pickle.loads(base64.b64decode(atom_structure))

    parse_trees_obs_value_pairs = []

    for element in result:
        subchain = []
        for condition in json.loads(element[7]):
            query_string = "select serialised_condition from path_condition_structure where id = %s;" % condition
            condition_string = cursor.execute(query_string).fetchone()[0]
            subchain.append(condition_string)

        path_condition_list_lhs = subchain[1:(element[4]+1)]
        path_condition_list_rhs = subchain[1:(element[5]+1)]
        lhs_path = edges_from_condition_sequence(scfg, path_condition_list_lhs, path_length_lhs)
        rhs_path = edges_from_condition_sequence(scfg, path_condition_list_rhs, path_length_rhs)
        path = rhs_path if (path_length_lhs < path_length_rhs) else lhs_path
        parse_tree = ParseTree(path, grammar, path[0]._source_state)

        lhs_obs = ast.literal_eval(element[0])
        rhs_obs = ast.literal_eval(element[1])
        for key in lhs_obs:
            lhs_value = lhs_obs[key]
        for key in rhs_obs:
            rhs_value = rhs_obs[key]
        observed_difference = rhs_value - lhs_value

        try:
            stack_left = formula._lhs._arithmetic_stack
        except:
            stack_left = []
        try:
            stack_right = formula._rhs._arithmetic_stack
        except:
            stack_right = []

        d = abs(apply_arithmetic_stack(stack_right, rhs_value) -
                apply_arithmetic_stack(stack_left, lhs_value))

        #sign=-1 if verdict value=0 and sign=1 if verdict is true
        sign=-1+2*(element[6])

        parse_trees_obs_value_pairs.append((parse_tree, lhs_value, rhs_value, sign*d, element[2]))

    parse_trees, value1, value2, severities, x_axis = zip(*parse_trees_obs_value_pairs)

    intersection = parse_trees[0].intersect(parse_trees[1:])

    main_path = intersection.read_leaves()
    main_lines = []
    parameter_lines = []
    for element in main_path:
        if type(element) is CFGEdge:
            try:
                line_number = element._instruction.lineno
                main_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    main_lines.append(line_number)
                except:
                    pass
        else:

            try:
                line_number = element._instruction.lineno
                parameter_lines.append(line_number)
            except:
                try:
                    line_number = element._structure_obj.lineno
                    parameter_lines.append(line_number)
                except:
                    pass

    path_parameters = []
    intersection.get_parameter_paths(intersection._root_vertex, [], path_parameters)

    parameter_value_indices_to_lhs_obs = {}
    parameter_value_indices_to_rhs_obs = {}
    parameter_value_indices_to_severities = {}
    parameter_value_indices_to_x_axis = {}
    subpaths = []

    if len(path_parameters) > 0:

        n_of_trees = len(parse_trees)
        for (n, parse_tree) in enumerate(parse_trees):
          subtree = parse_tree.get_parameter_subtree(path_parameters[0])
          subpath = subtree.read_leaves()
          if subpath in subpaths:
            subpath_index = subpaths.index(subpath)
          else:
            subpaths.append(subpath)
            subpath_index = len(subpaths)-1
          if subpath_index not in parameter_value_indices_to_times:
            parameter_value_indices_to_lhs_obs[subpath_index] = [value1[n]]
            parameter_value_indices_to_rhs_obs[subpath_index] = [value2[n]]
            parameter_value_indices_to_severities[subpath_index] = [severities[n]]
            parameter_value_indices_to_x_axis[subpath_index] = [x_axis[n]]
          else:
            parameter_value_indices_to_lhs_obs[subpath_index].append(value1[n])
            parameter_value_indices_to_rhs_obs[subpath_index].append(value2[n])
            parameter_value_indices_to_severities[subpath_index].append(severities[n])
            parameter_value_indices_to_x_axis[subpath_index].append(x_axis[n])

        lines_by_subpaths = []

        for (i, subpath) in enumerate(subpaths):
            lines = []
            for element in subpath:
                try:
                    line_number = element._instruction.lineno
                    lines.append(line_number)
                except:
                    try:
                        line_number = element._instruction._structure_obj.lineno
                        lines.append(line_number)
                    except:
                        pass

                # fill in gaps in lines
                final_lines = []
                for n in range(len(lines)-1):
                    final_lines += [m for m in range(lines[n], lines[n+1]+1)]

            if len(lines) == 1: final_lines = lines
            lines_by_subpaths.append({"lines": final_lines,
                                      "observations_lhs": parameter_value_indices_to_lhs_obs[i],
                                      "observations_rhs": parameter_value_indices_to_rhs_obs[i],
                                      "severities": parameter_value_indices_to_severities[i],
                                      "x": parameter_value_indices_to_x_axis[i]})
    else:

        lines_by_subpaths = []

    return_data = {
        "parameter_values": lines_by_subpaths,
        "main_lines": main_lines,
        "parameters": parameter_lines
    }

    # generate a hash of the data
    path_hash = hashlib.sha1()
    path_hash.update(json.dumps(return_data))
    path_hash.update(json.dumps(dict))
    path_hash = path_hash.hexdigest()
    # store the plot
    store_plot(cursor, path_hash, dict, return_data)
    connection.commit()

    connection.close()
    return_data["path_hash"] = path_hash
    return return_data


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


def stack_repr(op_list):
    str = ""
    for o in op_list:
        str += "%s " % o
    return str


def logical_repr(op_list, HTML):
    if HTML:
        str = "%s" % op_list[0].HTMLrepr()
        for op in op_list[1:]:
            str += ", %s" % op.HTMLrepr()
    else:
        str = "%s" % op_list[0]
        for op in op_list[1:]:
            str += ", %s" % op
    return str


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

ArithmeticMultiply.__repr__ = \
    lambda object: "* %.2f" % object._v

ArithmeticAdd.__repr__ = \
    lambda object: "+ %.2f" % object._v

ArithmeticTrueDivide.__repr__ = \
    lambda object: "/ %.2f" % object._v

ArithmeticSubtract.__repr__ = \
    lambda object: "- %.2f" % object._v

StateValueInInterval.__repr__ = \
    lambda Atom: "%s('%s')._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueInOpenInterval.__repr__ = \
    lambda Atom: "%s('%s')._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueEqualTo.__repr__ = \
    lambda Atom: "%s('%s').equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueTypeEqualTo.__repr__ = \
    lambda Atom: "%s('%s').type().equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueEqualToMixed.__repr__ = \
    lambda Atom: "%s('%s').equals(%s('%s'))" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLessThanStateValueMixed.__repr__ = \
    lambda Atom: "%s('%s') < %s('%s')" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLessThanEqualStateValueMixed.__repr__ = \
    lambda Atom: "%s('%s') <= %s('%s')" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthLessThanStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s('%s').length() < %s('%s').length()" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthLessThanEqualStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s('%s').length() <= %s('%s').length()" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthInInterval.__repr__ = \
    lambda Atom: "%s('%s').length()._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueLengthInOpenInterval.__repr__ = \
    lambda Atom: "%s('%s').length()._in(%s)" % (Atom._state, Atom._name, Atom._interval)

TransitionDurationInInterval.__repr__=\
    lambda Atom: "%s.duration()._in(%s)" % (Atom._transition, Atom._interval)

TransitionDurationInOpenInterval.__repr__=\
    lambda Atom: "%s.duration()._in(%s)" % (Atom._transition, Atom._interval)

TransitionDurationLessThanTransitionDurationMixed.__repr__=\
    lambda Atom: "%s.duration() < %s.duration()" % (Atom._lhs, Atom._rhs)

TransitionDurationLessThanEqualTransitionDurationMixed.__repr__=\
    lambda Atom: "%s.duration() <= %s.duration()" % (Atom._lhs, Atom._rhs)

TransitionDurationLessThanStateValueMixed.__repr__ = \
    lambda Atom: "%s.duration() < %s('%s')" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanEqualStateValueMixed.__repr__ = \
    lambda Atom: "%s.duration() <= %s('%s')" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s.duration() < %s('%s').length()" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanEqualStateValueLengthMixed.__repr__ = \
    lambda Atom: "%s.duration() <= %s('%s').length()" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TimeBetweenInInterval.__repr__ = \
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, Atom._interval)

TimeBetweenInOpenInterval.__repr__ = \
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, str(Atom._interval))

LogicalAnd.__repr__= \
    lambda object: 'land(%s)' % logical_repr(object.operands, HTML = False)

LogicalOr.__repr__= \
    lambda object: 'lor(%s)' % logical_repr(object.operands, HTML = False)

LogicalNot.__repr__ = \
    lambda object: 'lnot(%s)' % object.operand

"""HTML repr functions"""

StateValueInInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

StateValueInOpenInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

StateValueEqualTo.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.equals(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._value)

StateValueTypeEqualTo.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.type().equals(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._value)

StateValueEqualToMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s') %s</span>.equals(
        <span class="subatom" subatom-index="1">%s('%s') %s</span>)
        </span>""" % (atoms_list.index(Atom),
            Atom._lhs, Atom._lhs_name, stack_repr(Atom._lhs._arithmetic_stack),
            Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

StateValueLessThanStateValueMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s') %s</span> <
        <span class="subatom" subatom-index="1">%s('%s') %s</span>
        </span>""" % (atoms_list.index(Atom),
           Atom._lhs, Atom._lhs_name, stack_repr(Atom._lhs._arithmetic_stack),
           Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

StateValueLessThanEqualStateValueMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s') %s</span> <=
        <span class="subatom" subatom-index="1">%s('%s') %s</span>
        </span>""" % (atoms_list.index(Atom),
           Atom._lhs, Atom._lhs_name, stack_repr(Atom._lhs._arithmetic_stack),
           Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

StateValueLengthLessThanStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.length() %s<
        <span class="subatom" subatom-index="1">%s('%s')</span>.length() %s
        </span>""" % (atoms_list.index(Atom),
            Atom._lhs, Atom._lhs_name, stack_repr(Atom._lhs._arithmetic_stack),
            Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

StateValueLengthLessThanEqualStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.length() %s <=
        <span class="subatom" subatom-index="1">%s('%s')</span>.length() %s
        </span>""" % (atoms_list.index(Atom),
           Atom._lhs, Atom._lhs_name, stack_repr(Atom._lhs._arithmetic_stack),
           Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

StateValueLengthInInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.length()._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

StateValueLengthInOpenInterval.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="subatom" subatom-index="0">%s('%s')</span>.length()._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._state, Atom._name, Atom._interval)

TransitionDurationInInterval.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._transition, Atom._interval)

TransitionDurationInOpenInterval.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span>._in(%s)
        </span>""" % (atoms_list.index(Atom), Atom._transition, str(Atom._interval))

TransitionDurationLessThanTransitionDurationMixed.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="duration"><span class="subatom" subatom-index="1">%s</span>.duration()</span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._rhs)

TransitionDurationLessThanEqualTransitionDurationMixed.HTMLrepr=\
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <=
        <span class="duration"><span class="subatom" subatom-index="1">%s</span>.duration()</span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs, Atom._rhs)

TransitionDurationLessThanStateValueMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="subatom" subatom-index="1">%s('%s') %s </span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs,
            Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

TransitionDurationLessThanEqualStateValueMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <=
        <span class="subatom" subatom-index="1">%s('%s') %s </span>
        </span>""" % (atoms_list.index(Atom), Atom._lhs,
           Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

TransitionDurationLessThanStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <
        <span class="subatom" subatom-index="1">%s('%s')</span>.length() %s
        </span>""" % (atoms_list.index(Atom), Atom._lhs,
            Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

TransitionDurationLessThanEqualStateValueLengthMixed.HTMLrepr = \
    lambda Atom: """<span class="atom" atom-index="%i">
        <span class="duration"><span class="subatom" subatom-index="0">%s</span>.duration()</span> <=
        <span class="subatom" subatom-index="1">%s('%s')</span>.length() %s
        </span>""" % (atoms_list.index(Atom), Atom._lhs,
           Atom._rhs, Atom._rhs_name, stack_repr(Atom._rhs._arithmetic_stack))

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
    lambda object: 'land(%s)' % logical_repr(object.operands, HTML = True)

LogicalOr.HTMLrepr= \
    lambda object: 'lor(%s)' % logical_repr(object.operands, HTML = True)

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
