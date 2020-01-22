"""
Module to provide functions to query the verdict database for the analysis library.
"""
from .utils import get_connection
import sqlite3
import json


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


def get_path_conditions_by_function_call_id(call_id):
    """Given a function call id, get the serialised conditions used for path reconstruction through that function
    call. """
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    query_string = "select * from path_condition where function_call = ?"
    path_condition_dicts = cursor.execute("select * from path_condition where function_call = ?", [call_id]).fetchall()
    path_condition_ids = map(lambda path_cond_dict : path_cond_dict["serialised_condition"], path_condition_dicts)
    # extract the path condition ids, then get the serialised path conditions
    serialised_conditions = list(map(
        lambda path_condition_id : cursor.execute(
            "select serialised_condition from path_condition_structure where id=?",
            [path_condition_id]
        ).fetchone()["serialised_condition"],
        path_condition_ids
    ))
    connection.close()
    return json.dumps(serialised_conditions)


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