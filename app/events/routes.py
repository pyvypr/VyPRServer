"""
Functions used as end points to serve event streams to the VyPR visualisation tool.
"""
from .. import app_object
from .database import   (get_events,
                        insert_instrumentation_event,
                        insert_monitoring_event,
                        get_function_name_to_code_map)
from flask import request, jsonify, render_template, Response
from flask_cors import cross_origin
import json
import time


@app_object.route("/event_stream/add/instrumentation/", methods=["POST"])
def add_to_instrumentation_stream():
    """
    Given an action, event data and a time, add an instrumentation event.
    :return: Success or failure
    """
    request_data_dictionary = json.loads(request.get_data())
    result = insert_instrumentation_event(
        request_data_dictionary["action"],
        request_data_dictionary["data"],
        request_data_dictionary["time_added"]
    )
    if result:
        return "Success"
    else:
        return "Failure"

@app_object.route("/event_stream/add/monitoring/", methods=["POST"])
def add_to_monitoring_stream():
    """
    Given an action, event data and a time, add a monitoring event.
    :return: Success or failure
    """
    request_data_dictionary = json.loads(request.get_data())
    result = insert_monitoring_event(
        request_data_dictionary["action"],
        request_data_dictionary["data"],
        request_data_dictionary["time_added"]
    )
    if result:
        return "Success"
    else:
        return "Failure"


@app_object.route("/event_stream/instrumentation/", methods=["GET"])
@cross_origin()
def inst_stream():
    """
    Sends all existing instrumentation events.  For instrumentation, we don't stream
    because instrumentation is a short-running process.
    :return: List of dicts
    """
    existing_events, _ = get_events("instrumentation")
    return Response(json.dumps(existing_events), mimetype="text/html")


@app_object.route("/event_stream/monitoring/", methods=["GET"])
@cross_origin()
def mon_stream():
    """
    Streams monitoring events to a client.
    First, get all existing monitoring events and push those along the stream.
    Then, in a loop with a 1 second delay, query the verdict database for events added in the last second.
    :return: Stream
    """
    results, _ = get_events("monitoring")
    function_name_to_code = get_function_name_to_code_map()
    results = {
        "events" : results,
        "code_map" : function_name_to_code
    }
    return Response(json.dumps(results), mimetype="text/html")

    """def stream_generator():
        # first, we get all events up until now
        events, start_time = get_events("monitoring")
        response_string = "\n\n".join(map(lambda event : "data: %s" % event, events))
        # we yield this result
        yield response_string
        while True:
            # now, we get all events from the previous time up until the new current time
            new_events, prov_start_time = get_events("monitoring", start_time)
            if len(new_events) == 0:
                continue
            else:
                start_time = prov_start_time
            response_string = "\n\n".join(map(lambda event: "data: %s" % event, new_events))
            # yield this result and sleep for 1 second
            yield response_string
            time.sleep(1)

    # return the generator as a response
    return Response(stream_generator(), mimetype="text/event-stream")"""