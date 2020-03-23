"""
Module to provide functions for verdict database insertion.
"""
from .utils import get_connection
import json
import traceback
import pickle


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

    # construct program path and add a json form of the sequence to the row function_call row

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

    # perform the function call insertion

    cursor.execute(
        "insert into function_call (function, time_of_call, end_time_of_call, trans, path_condition_id_sequence)"
        "values(?, ?, ?, ?, ?)",
        [function_id, call_data["time_of_call"], call_data["end_time_of_call"], transaction_id,
         json.dumps(new_program_path)])
    function_call_id = cursor.lastrowid
    connection.commit()

    print("function call created")

    connection.commit()
    connection.close()

    print("program path created")

    return {"function_call_id": function_call_id, "function_id": function_id}


def insert_verdicts(verdict_dictionary):
    connection = get_connection()
    cursor = connection.cursor()

    print("Performing verdicts insertion")

    function_call_id = verdict_dictionary["function_call_id"]

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

        # create the verdict
        # we don't check for an existing verdict - there won't be repetitions here
        cursor.execute(
            "insert into verdict (binding, verdict, time_obtained, function_call, collapsing_atom,"
            "collapsing_atom_sub_index) values (?, ?, ?, ?, ?, ?)",
            [new_binding_id, verdict_value, verdict_time_obtained, function_call_id, collapsing_atom_index,
             collapsing_atom_sub_index])
        new_verdict_id = cursor.lastrowid

        print("inserted verdict - now performing observation insertion")

        for atom_index in observations_map:
            # insert observation(s) for this atom_index
            print(observations_map[atom_index])
            for sub_index in observations_map[atom_index].keys():
                last_condition = path_map[atom_index][sub_index]
                cursor.execute(
                    "insert into observation (instrumentation_point, verdict, observed_value, observation_time, "
                    "observation_end_time, previous_condition_offset, atom_index, sub_index) "
                    "values(?, ?, ?, ?, ?, ?, ?, ?)",
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