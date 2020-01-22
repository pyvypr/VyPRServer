"""
Utility functions - these should be moved to another module.
"""
from VyPR.QueryBuilding import *
from VyPR.monitor_synthesis.formula_tree import *
import pickle


def friendly_bind_variable(bind_variable):
    if type(bind_variable) is StaticState:
        return "Forall(%s = changes(%s)).\\" % (bind_variable._bind_variable_name, bind_variable._name_changed)
    elif type(bind_variable) is StaticTransition:
        return "Forall(%s = calls(%s)).\\" % (bind_variable._bind_variable_name, bind_variable._operates_on)


def friendly_atom(atom):
    if type(atom) is TransitionDurationInInterval:
        return "%s.duration()._in((%s, %s))" % (atom._transition, atom._interval[0], atom._interval[1])
    elif type(atom) is StateValueInInterval:
        return "%s(%s)._in((%s, %s))" % (atom._state, atom._name, atom._interval[0], atom._interval[1])
    elif type(atom) is StateValueInOpenInterval:
        return "%s <= value of %s in %s <= %s" % (atom._interval[0], atom._name, atom._state, atom._interval[1])
    elif type(atom) is StateValueEqualTo:
        return "value of %s in %s = %s" % (atom._name, atom._state, atom._value)


def get_bind_variable_names(bind_variables):
    return map(lambda bind_variable: bind_variable._bind_variable_name, bind_variables)


def friendly_variable_in_formula(variable):
    return "%s" % variable._bind_variable_name


def deserialise_property_tree(property_tree, path=[]):
    """
    recurse on the property tree to deserialise the properties that are stored there.
    """
    if len(path) == 0:
        # we're at the root
        for key in property_tree.keys():
            property_tree[key] = deserialise_property_tree(property_tree, [key])

        return property_tree
    else:
        # we have a path, so go down to the subtree
        subtree = property_tree[path[0]]
        for item in path[1:]:
            subtree = subtree[item]

        if type(subtree) is tuple:
            # if the subtree is just a tuple, we're at a leaf
            subtree = list(subtree)
            property_dictionary = json.loads(subtree[3])
            TransitionDurationInInterval.__repr__ = friendly_atom
            StaticState.__repr__ = friendly_variable_in_formula
            StaticTransition.__repr__ = friendly_variable_in_formula
            subtree.append(str(pickle.loads(property_dictionary["property"])))
            subtree.append("%s" % ", ".join(
                map(friendly_bind_variable, pickle.loads(property_dictionary["bind_variables"]).values())))
            subtree.append(
                ", ".join(get_bind_variable_names(pickle.loads(property_dictionary["bind_variables"]).values())))

            return subtree
        elif type(subtree) is list:
            for n in range(len(subtree)):
                subtree[n] = deserialise_property_tree(property_tree, path + [n])
            return subtree
        else:
            # if not, we have a further subtree
            for next_item in subtree.keys():
                subtree[next_item] = deserialise_property_tree(property_tree, path + [next_item])

            return subtree


def deserialise_property(dictionary):
    """
    Given the bind variables and formula of a property, use the classes from VyPR to deserialise it and
    form its string representation.
    """
    # override the string representation methods
    TransitionDurationInInterval.__repr__ = friendly_atom
    StaticState.__repr__ = friendly_variable_in_formula
    StaticTransition.__repr__ = friendly_variable_in_formula

    # deserialise
    return {
        "property": str(pickle.loads(dictionary["property"])),
        "bind_variables": "%s" % ", ".join(
            map(friendly_bind_variable, pickle.loads(dictionary["bind_variables"]).values())),
        "bind_variable_names": ", ".join(get_bind_variable_names(pickle.loads(dictionary["bind_variables"]).values()))
    }