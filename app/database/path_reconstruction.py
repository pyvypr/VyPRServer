"""
Path reconstruction functions.
"""
import json

from .utils import get_connection
from VyPR.SCFG.construction import CFG, CFGVertex, CFGEdge
from VyPR.SCFG.parse_tree import ParseTree
from VyPR.monitor_synthesis.formula_tree import LogicalNot


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


def compute_condition_sequence_and_path_length(observation_id):
    """
    Given an observation ID, find the path condition sequence leading to that observation.
    """

    connection = get_connection()
    cursor = connection.cursor()

    condition_sequence_and_path_length = observation_id_to_condition_sequence_and_path_length(cursor, observation_id)

    connection.close()

    return condition_sequence_and_path_length


def construct_new_search_tree(connection, cursor, scfg, root_observation, observation_list, instrumentation_point_id):
    """
    Given a list of observations and an instrumentation point id, construct a new search tree.
    """

    # create a new root vertex
    # the intersection held by the root vertex must be empty - intersection over one observation doesn't
    # really make a lot of sense
    cursor.execute("insert into search_tree_vertex (observation, intersection, parent_vertex) values(?, -1, -1)",
                   [root_observation])
    search_tree_vertex_root_id = cursor.lastrowid

    # compute the sequence of intersections

    root_path = reconstruct_path(cursor, scfg, root_observation)
    root_parse_tree = ParseTree(root_path, scfg.derive_grammar(), scfg.starting_vertices)
    child_path = reconstruct_path(cursor, scfg, observation_list[0])
    child_parse_tree = ParseTree(child_path, scfg.derive_grammar(), scfg.starting_vertices)

    initial_intersection = root_parse_tree.intersect([child_parse_tree])
    previous_intersection_result = initial_intersection

    # acts as a map from observation id index to intersection
    intersections = [initial_intersection]
    for obs in observation_list[1:]:
        path = reconstruct_path(cursor, scfg, obs)
        new_parse_tree = ParseTree(path, scfg.derive_grammar(), scfg.starting_vertices, parametric=True)
        new_intersection = previous_intersection_result.intersect([new_parse_tree])
        intersections.append(new_intersection)

    condition_sequences = []
    for intersection in intersections:
        parametric_path = intersection.read_leaves()
        condition_sequences.append(path_to_condition_sequence(cursor, parametric_path))

    print(condition_sequences)

    # insert the rest of the observations
    insert_observations_from_vertex(connection, cursor, observation_list, search_tree_vertex_root_id,
                                    condition_sequences)
    # create a new search tree, and insert a path for the current set
    cursor.execute("insert into search_tree (root_vertex, instrumentation_point) values(?, ?)",
                   [search_tree_vertex_root_id, instrumentation_point_id])
    new_search_tree_id = cursor.lastrowid
    connection.commit()

    # return the condition sequence associated with the leaf
    return condition_sequences[-1]


def insert_observations_from_vertex(connection, cursor, observations, vertex_id, condition_sequences):
    """
    Given a list of observations, a vertex id in search tree and a list of path condition sequences,
    add the new path starting from that vertex.
    """
    print("inserting new path for observation sequence %s from vertex %i" % (str(observations), vertex_id))
    parent_vertex_id = vertex_id
    for (n, obs) in enumerate(observations):

        # if we're at the last observation, attach the leaf to the intersection
        condition_sequence_string = json.dumps(condition_sequences[n])
        # attempt to find the condition sequence in the intersection table
        existing_intersection = cursor.execute(
            "select id from intersection where condition_sequence_string = ?",
            [condition_sequence_string]
        ).fetchall()
        if len(existing_intersection) > 0:
            intersection_id = existing_intersection[0][0]
        else:
            cursor.execute("insert into intersection (condition_sequence_string) values(?)",
                           [condition_sequence_string])
            intersection_id = cursor.lastrowid

        cursor.execute("insert into search_tree_vertex (observation, intersection, parent_vertex) values(?, ?, ?)",
                       [obs, intersection_id, parent_vertex_id])
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
        elif n == len(function_qualifier) - 1:
            tokens.append(function_qualifier[last_position:])

    return tokens


def construct_function_scfg(function):
    """
    Given a function name, find the function definition in the service code and construct the SCFG.
    """

    module = function[0:function.rindex(".")]
    function = function[function.rindex(".") + 1:]

    file_name = module.replace(".", "/") + ".py.inst"
    file_name_without_extension = module.replace(".", "/")

    # extract asts from the code in the file
    config_dict = json.load(open('config.json'))
    monitored_service = config_dict["monitored_service"]
    code = "".join(open(os.path.join(monitored_service, file_name), "r").readlines())
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
            lambda entry: (type(entry) is ast.ClassDef and
                           entry.name == step),
            current_step
        )[0]

    # find the final function definition

    function_def = filter(
        lambda entry: (type(entry) is ast.FunctionDef and
                       entry.name == actual_function_name),
        current_step.body if type(current_step) is ast.ClassDef else current_step
    )[0]

    # construct the scfg of the code inside the function
    scfg = CFG()
    scfg_vertices = scfg.process_block(function_def.body)

    return scfg


def edges_from_condition_sequence(scfg, path_subchain, instrumentation_point_path_length):
    """
    Given a sequence of (deserialised) conditions in path_subchain and the final path length,
    reconstruct a path through the scfg, including loop multiplicity.
    """
    condition_index = 0
    curr = scfg.starting_vertices
    # path = [curr]
    path = []
    cumulative_conditions = []
    while condition_index < len(path_subchain):
        # path.append(curr)
        # print(curr._name_changed)
        if len(curr.edges) > 1:
            # more than 1 outgoing edges means we have a branching point

            # TODO: need to handle parameters in condition sequences
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
                print("traversing conditional %s with condition %s" % (curr, path_subchain[condition_index]))
                # search the outgoing edges for an edge whose condition has the same length as path_subchain[
                # condition_index]
                for edge in curr.edges:
                    print("testing edge condition %s against condition %s" % \
                          (edge._condition[-1], path_subchain[condition_index][0]))
                    # for now we assume that conditions are single objects (ie, not conjunctions)
                    if type(edge._condition[-1]) == type(path_subchain[condition_index][0]):
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
                if not (type(path_subchain[condition_index]) is LogicalNot):
                    # condition isn't a negation, so follow the edge leading into the loop
                    for edge in curr.edges:
                        if not (type(edge._condition) is LogicalNot):
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
                    print("testing edge with condition %s against cumulative condition %s" % \
                          (edge._condition, cumulative_conditions + [path_subchain[condition_index]]))
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
                if not (type(path_subchain[condition_index]) is LogicalNot):
                    # go back to the start of the loop without consuming the condition
                    print("going back around the loop")
                    relevant_edge = filter(lambda edge: edge._condition == 'loop-jump', curr.edges)[0]
                    curr = relevant_edge._target_state
                    path.append(relevant_edge)
                else:
                    # go past the loop
                    print(curr.edges)
                    print("ending loop")
                    relevant_edge = filter(lambda edge: edge._condition == 'post-loop', curr.edges)[0]
                    curr = relevant_edge._target_state
                    path.append(relevant_edge)
                    # consume the negative condition
                    condition_index += 1

            print("condition index %i from condition chain length %i" % (condition_index, len(path_subchain)))
        elif curr._name_changed == ["post-conditional"]:
            print("traversing post-conditional")
            # check the next vertex - if it's also a post-conditional, we move to that one but don't consume the
            # condition if the next vertex isn't a post-conditional, we consume the condition and move to it
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
    limit = instrumentation_point_path_length - 1 if len(path_subchain) > 0 else instrumentation_point_path_length
    for i in range(limit):
        # path.append(curr)
        path.append(curr.edges[0])
        curr = curr.edges[0]._target_state

    # path.append(curr)

    return path


def deserialise_condition(serialised_condition):
    if serialised_condition != "":
        if not (serialised_condition in ["conditional exited", "try-catch exited", "try-catch-main", "parameter",
                                         "exit conditional"]):
            # unserialised_condition = pickle.loads(serialised_condition)
            unserialised_condition = serialised_condition
        else:
            unserialised_condition = serialised_condition
    else:
        unserialised_condition = None
    return unserialised_condition


def observation_id_to_condition_sequence_and_path_length(cursor, observation_id):
    """
    Given an observation, determine the sequence of path conditions satisfied to reach it.
    This will be used for path reconstruction on the client side.
    """

    observation = cursor.execute(
        """
select verdict.function_call, observation.instrumentation_point, observation.previous_condition_offset
from
((observation inner join verdict on observation.verdict == verdict.id)
    inner join function_call on verdict.function_call == function_call.id)
where observation.id == ?
""", [observation_id]).fetchall()[0]

    function_call_id = observation[0]
    instrumentation_point_id = observation[1]
    previous_condition_offset = observation[2]

    # get the path condition id sequence

    path_condition_id_sequence = json.loads(
        cursor.execute(
            "select path_condition_id_sequence from function_call where id = ?", [function_call_id]
        ).fetchone()[0]
    )

    # map each id to a condition

    path_condition_sequence = list(map(
        lambda path_condition_id: cursor.execute(
            "select serialised_condition from path_condition_structure where id=?",
            [path_condition_id]
        ).fetchone()[0],
        path_condition_id_sequence
    ))

    # get the prefix according to the offset held by the observation
    # also, remove the first condition - this is an empty condition

    path_subchain = path_condition_sequence[1:previous_condition_offset+1]

    instrumentation_point_path_length = int(
        cursor.execute(
            "select reaching_path_length from instrumentation_point where id = ?",
            [instrumentation_point_id]
        ).fetchall()[0][0]
    )

    # path_subchain = list(map(pickle.dumps, path_subchain))

    return {"path_subchain": path_subchain, "path_length": instrumentation_point_path_length}


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
    path_conditions = cursor.execute("select * from path_condition where function_call = ?",
                                     [function_call_id]).fetchall()
    for path_condition in path_conditions:
        # check if there are any other path conditions that refer to this one
        # if there are none, we have the first one
        check = cursor.execute("select * from path_condition where function_call = ? and next_path_condition = ?",
                               [function_call_id, path_condition[0]]).fetchall()
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
        current_path_condition = \
            cursor.execute("select * from path_condition where id = ?", [current_path_condition_id]).fetchall()[0]
        current_path_condition_id = current_path_condition[-2]
        serialised_condition_id = current_path_condition[1]
        serialised_condition = \
            cursor.execute("select * from path_condition_structure where id = ?", [serialised_condition_id]).fetchall()[
                0][
                1]
        unserialised_condition = deserialise_condition(serialised_condition)
        path_chain.append(unserialised_condition)

    print(path_id_chain)
    print(path_chain)

    # remove the first condition, since it's None
    path_chain = path_chain[1:]

    instrumentation_point_path_length = int(
        cursor.execute(
            "select reaching_path_length from instrumentation_point where id = ?",
            [instrumentation_point_id]
        ).fetchall()[0][0]
    )

    print("reconstructing path for observation %s with previous condition %i and value %s based on chain %s" % \
          (observation_id, previous_path_condition_entry, str(observed_value), path_chain))

    # traverse the SCFG based on the derived condition chain
    path_subchain = path_chain[0:path_id_chain.index(previous_path_condition_entry)]
    print("traversing using condition subchain %s" % path_subchain)

    path = edges_from_condition_sequence(scfg, path_subchain, instrumentation_point_path_length)

    print("reconstructed path is %s" % path)

    return path


def reconstruct_paths(cursor, scfg, observation_ids):
    """
    Given a sequence of observations
    """
    return map(lambda observation_id: reconstruct_path(cursor, scfg, observation_id), observation_ids)


def path_to_condition_sequence(cursor, path, parametric=False):
    """
    Iterate through the path given, converting it to a sequence of condition IDs.
    """
    print("converting to condition sequence")
    print(path)
    # initialise the condition sequence with the empty condition
    # NOTE: this might break for loops... we'll see
    condition_sequence = [""] if not (parametric) else [pickle.dumps(path[0]._condition)]
    for (n, el) in enumerate(path):
        print("processing %s" % str(el))

        if type(el) is CFGEdge:
            if el._operates_on == ["control-flow"]:
                if n != len(path) - 1:
                    if type(path[n + 1]) is CFGVertex:
                        condition_sequence.append("parameter")
                        if el._condition == 'conditional':
                            condition_sequence.append("exit conditional")
                    else:
                        if el._condition == 'conditional':
                            # index_of_branch_taken = map(lambda edge : edge._condition, el._target_state.edges).index(path[n+1]._condition)
                            # condition_sequence.append(index_of_branch_taken)
                            condition_sequence.append(pickle.dumps(path[n + 1]._condition))

                        elif el._condition == 'post-condition':
                            condition_sequence.append("exit conditional")
            elif el._instruction == "loop":
                condition_sequence.append(pickle.dumps(el._condition))
            elif el._instruction == "loop-jump":
                condition_sequence.append("loop-jump")
            elif el._instruction == "post-loop":
                condition_sequence.append(pickle.dumps(LogicalNot("dummy")))

    return condition_sequence


def construct_parametric_path(scfg, paths, grammar_rules_map, read_leaves=True):
    """
    Given an SCFG and a list of paths obtained by reconstruction,
    compute the parse trees and then give the intersection.
    """
    # compute parse trees
    parse_trees = []
    for (path_index, path) in enumerate(paths):
        print("=" * 100)
        print("constructing parse tree for path")
        print(path)

        parse_tree = ParseTree(path, grammar_rules_map, scfg.starting_vertices)

        parse_trees.append(parse_tree)
        generated_path = parse_tree._path_progress

        print("path generated by parse tree:")
        print(generated_path)

    # intersect the parse trees
    intersection = parse_trees[0].intersect(parse_trees[1:])
    if read_leaves:
        # read the parametric path from the intersection
        parametric_path = []
        intersection.leaves_to_left_right_sequence(intersection._root_vertex, parametric_path)
        return parametric_path
    else:
        return intersection
