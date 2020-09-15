"""
Module to handle operations on events database for visualisation.
"""
import sqlite3
import datetime
import traceback
import dateutil
import json
import ast
import os

import app
from VyPR.SCFG.construction import CFG, CFGVertex, CFGEdge


def connect():
    """
    Get a connection to the events database, currently sqlite.
    :return: sqlite connection
    """
    connection = sqlite3.connect(app.events_database_string)
    return connection


def verdict_connect():
    """
    Get a connection to the verdicts database.
    """
    connection = sqlite3.connect(app.database_string)
    return connection


"""
The following SCFG functions need to be refactored into a common module.
"""


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
    print(os.getcwd())
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
    print("reconstruction with path subchain %s" % str(path_subchain))
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

    print("finishing path traversal at vertex %s with path length %i" % (curr, instrumentation_point_path_length))

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


def get_events(type, start_time=None):
    """
    Get all events that currently exist for the given type.
    :return: List of event dictionaries created by instrumentation.
    """
    con = connect()
    con.row_factory = sqlite3.Row
    cursor = con.cursor()

    verdict_con = verdict_connect()
    verdict_cursor = verdict_con.cursor()

    if not start_time:
        # set the start time to long ago enough to capture all events
        #start_time = datetime.datetime.now() - datetime.timedelta(minutes=1000000)
        # set start time to the epoch
        start_time = datetime.datetime.utcfromtimestamp(0)

    # fix a time up to which we are taking events, so we know from
    # which time to start the next time we poll for events
    end_time = datetime.datetime.now()
    events = cursor.execute(
        "select * from event where type = ? and time_added > ? and time_added <= ?",
        [type, start_time, end_time]
    ).fetchall()
    events = map(dict, events)

    # get an scfg object
    if type == "monitoring":
        print("function from first event:")
        print(json.loads(events[0]["data"])["function"])
        scfg = get_scfg(json.loads(events[0]["data"])["function"], app.monitored_service_path)

    for n in range(len(events)):
        events[n]["data"] = json.loads(events[n]["data"])
        if type == "monitoring":
            # if the event is from monitoring and the action is "receive-measurement"
            # then we need to extract the path information from the event data,
            # reconstruct the path over the SCFG and get the line number
            if events[n]["action_to_perform"] == "receive-measurement":
                print(events[n]["data"]["path"])
                path_condition_ID_sequence = events[n]["data"]["path"]["path_condition_sequence"]
                instrumentation_point_ID = events[n]["data"]["path"]["instrumentation_point_db_id"]
                # get the reaching path length from the verdicts db
                reaching_path_length = verdict_cursor.execute(
                    "select reaching_path_length from instrumentation_point where id = ?",
                    [instrumentation_point_ID]
                ).fetchone()[0]
                # get path conditions from each ID in path_condition_ID_sequence
                path_condition_sequence = []
                for condition_id in path_condition_ID_sequence:
                    path_condition = verdict_cursor.execute(
                        "select serialised_condition from path_condition_structure where id = ?",
                        [condition_id]
                    ).fetchone()[0]
                    path_condition_sequence.append(path_condition)
                events[n]["data"]["path"]["reaching_path_length"] = reaching_path_length
                events[n]["data"]["path"]["path_condition_sequence"] = path_condition_sequence
                # reconstruct the path to the relevant observation
                edge_sequence = edges_from_condition_sequence(scfg, path_condition_sequence, reaching_path_length)
                print(edge_sequence)
                final_line_number = edge_sequence[-1]._instruction.lineno
                events[n]["data"]["line_number"] = final_line_number


    con.close()
    verdict_con.close()
    # we return the end time so that next time we can get events after this point
    return events, end_time


def get_function_name_to_code_map():
    """
    Go through all instrumentation events and construct a map from function names to source code
    to be used in visualisation of monitoring.
    :return: a dictionary mapping from function names to lists of lines of their source code.
    """
    con = connect()
    cursor = con.cursor()

    instrumentation_events = cursor.execute("select data from event where "
                                            "action_to_perform = 'begin_function_processing'").fetchall()
    function_to_code = {}
    for event in instrumentation_events:
        function_name = json.loads(event[0])["function_name"]
        if function_name not in function_to_code:
            function_to_code[function_name] = json.loads(event[0])["code"]

    return function_to_code



def insert_instrumentation_event(action, data, time):
    """
    Given an action, some data and an event time, create a new row in the event table.
    :param action:
    :param data:
    :param time:
    :return: Success or failure
    """
    con = connect()
    cursor = con.cursor()

    try:
        cursor.execute("insert into event (type, action_to_perform, data, time_added) values(?, ?, ?, ?)",
                       ["instrumentation", action, data, dateutil.parser.isoparse(time)])
        con.commit()
        return True
    except:
        traceback.print_exc()
        return False

def insert_monitoring_event(action, data, time):
    """
    Given an action, some data and an event time, create a new row in the event table.
    :param action:
    :param data:
    :param time:
    :return: Success or failure
    """
    con = connect()
    cursor = con.cursor()

    try:
        cursor.execute("insert into event (type, action_to_perform, data, time_added) values(?, ?, ?, ?)",
                       ["monitoring", action, data, dateutil.parser.isoparse(time)])
        con.commit()
        return True
    except:
        traceback.print_exc()
        return False
