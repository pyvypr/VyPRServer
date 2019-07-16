import database
import json
from app import app_object

@app_object.route("/client/list_functions_2")
def list_functions_2():
	return database.list_functions2()

@app_object.route("/client/list_function_calls_f/<function_name>/")
def list_function_calls_f(function_name):
	return database.list_calls_function(function_name)

@app_object.route("/client/list_function_calls_http/<http_request_id>/")
def list_function_calls_http(http_request_id):
	return database.list_calls_http(http_request_id)

@app_object.route("/client/list_function_calls_http_id/<http_request_id>/<function_id>/")
def list_function_calls_http_id(http_request_id,function_id):
	return database.list_calls_httpid(http_request_id,function_id)

@app_object.route("/client/get_function_by_name/<function_name>/")
def get_function_by_name(function_name):
	return database.get_f_byname(function_name)

@app_object.route("/client/get_function_by_id/<function_id>/")
def get_function_by_id(function_id):
	return database.get_f_byid(function_id)

@app_object.route("/client/get_http_by_id/<http_request_id>/")
def get_http_by_id(http_request_id):
	return database.get_http_byid(http_request_id)

@app_object.route("/client/get_call_by_id/<call_id>/")
def get_call_by_id(call_id):
	return database.get_call_byid(call_id)

@app_object.route("/client/get_http_by_time/<time_of_request>/")
def get_http_by_time(time_of_request):
   return database.get_http_bytime(time_of_request)

@app_object.route("/client/get_verdict_by_id/<verdict_id>/")
def get_verdict_by_id(verdict_id):
	return database.get_verdict_byid(verdict_id)

@app_object.route("/client/get_atom_by_id/<atom_id>/")
def get_atom_by_id(atom_id):
	return database.get_atom_byid(atom_id)

@app_object.route("/client/get_atom_by_index/<atom_index>/")
def get_atom_by_index(atom_index):
	return database.get_atom_byindex(atom_index)

@app_object.route("/client/list_atoms_where_verdict/<verdict_value>/")
def list_atoms_where_verdict(verdict_value):
	return database.list_atoms_verdict(verdict_value)

@app_object.route("/client/first_observation_of_call_fail/<call_id>/")
def first_observation_of_call_fail(call_id):
	return database.first_observation_failed_verdict(call_id)
