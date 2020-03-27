"""
Module to provide functions for the web analysis tool to use.
"""
from .utils import get_connection
import json
import pprint
import pickle
import base64
from VyPR.monitor_synthesis.formula_tree import *
from VyPR.QueryBuilding.formula_building import *


"""
list of changed repr methods follows - just for class Atom for now
for each type of atom, it should display it similar to how it was given in the specification
"""

StateValueInInterval.__repr__=\
    lambda Atom: "%s(%s)._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueInOpenInterval.__repr__=\
    lambda Atom: "%s(%s)._in(%s)" % (Atom._state, Atom._name, Atom._interval)

StateValueEqualTo.__repr__=\
    lambda Atom: "%s(%s).equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueTypeEqualTo.__repr__=\
    lambda Atom: "%s(%s).type().equals(%s)" % (Atom._state, Atom._name, Atom._value)

StateValueEqualToMixed.__repr__=\
    lambda Atom: "%s(%s).equals(%s(%s))" % (Atom._lhs, Atom._lhs_name, Atom._rhs, Atom._rhs_name)

StateValueLengthInInterval.__repr__=\
    lambda Atom: "%s(%s).length()._in(%s)" % (Atom._state, Atom._name, Atom._interval)

TransitionDurationInInterval.__repr__=\
    lambda Atom: "(%s).duration()._in(%s)" % (Atom._transition, Atom._interval)

TransitionDurationLessThanTransitionDurationMixed.__repr__=\
    lambda Atom: "(%s).duration() < (%s).duration()" % (Atom._lhs, Atom._rhs)

TransitionDurationLessThanStateValueMixed.__repr__=\
    lambda Atom: "%s.duration() < %s(%s)" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TransitionDurationLessThanStateValueLengthMixed.__repr__ =\
    lambda Atom: "%s.duration() < %s(%s).length()" % (Atom._lhs, Atom._rhs, Atom._rhs_name)

TimeBetweenInInterval.__repr__=\
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, Atom._interval)

TimeBetweenInOpenInterval.__repr__=\
    lambda Atom: "timeBetween(%s, %s)._in(%s)" % (Atom._lhs, Atom._rhs, str(Atom._interval))



"""
we need to display states also similar to how they are defined in the specification
new function because other __repr__ is also needed
TODO: other possible states ??
"""


StaticState.my_repr_function=\
    lambda object: "%s = changes(%s)"%(object._bind_variable_name, object._name_changed)

StaticTransition.my_repr_function=\
    lambda object: "%s = calls(%s)"%(object._bind_variable_name, object._operates_on)






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

        print(function[1])

        full_name = function[1]

        # the hierarchy also includes the machine name (server/client) separated by a hyphen
        machine_rest = full_name.split("-")
        machine = [machine_rest[0]]
        path_rest = machine_rest[1].split(".")

        # finally, the name of the function is separated with a colon sometimes
        last = path_rest[-1].split(":")
        path_rest = path_rest[0:-1]+last
        path = machine + path_rest

        print(path)

        if not (dictionary_tree_structure.get(path[0])):
            dictionary_tree_structure[path[0]] = {}
        current_hierarchy_step = dictionary_tree_structure[path[0]]
        # iterate through the rest of the path
        for item in path[1:-1]:
            if not (current_hierarchy_step.get(item)):
                current_hierarchy_step[item] = {}
            current_hierarchy_step = current_hierarchy_step[item]

        hash = function[2]
        prop = pickle.loads(base64.b64decode(json.loads(function[3])["property"]))
        bind_var = pickle.loads(base64.b64decode(json.loads(function[3])["bind_variables"]))
        print(prop)
        print(bind_var)

        atom_str = str(prop)

        spec = ''
        vars = ''

        #vars will save a list of variables as "x, y, z" - used later in lambda
        #spec begins with Forall(...) - each variable generates one of these
        for var in bind_var.items():
            atom_str = atom_str.replace(str(var[1]),var[0])
            if spec:
                vars += ", "
            spec += '<p class="list-group-item-text code">Forall(%s).</p>'% var[1].my_repr_function()
            vars += var[0]

        #finally, add the condition stored in atom_str to the specification
        spec +="""<p class="list-group-item-text code">Check(</p>
            <p class="list-group-item-text code">&nbsp;&nbsp;lambda %s : (</p>
            <p class="list-group-item-text code">&nbsp;&nbsp;&nbsp;&nbsp; %s </p>
            <p class="list-group-item-text code">&nbsp;&nbsp;)</p> 
            <p class="list-group-item-text code">)</p>"""%(vars,atom_str)

        #and store pairs (hash,specification) as leaves
        if current_hierarchy_step.get(path[-1]):
            current_hierarchy_step[path[-1]].append([hash,spec])
        else:
            current_hierarchy_step[path[-1]] = [[hash,spec]]

    #pprint(dictionary_tree_structure)

    connection.close()
    dictionary_tree_structure["client"]={"app":[[hash,spec]]}
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
