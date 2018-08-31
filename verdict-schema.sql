create table function (
	id integer primary key autoincrement,
	fully_qualified_name text not null,
	property text not null,
	foreign key(property) references property(hash)
);

create table property (
	hash text primary key,
	serialised_structure text not null
);

create table binding (
	id integer primary key autoincrement,
	binding_space_index int not null,
	function int not null,
	binding_statement_lines text not null,
	foreign key(function) references function(id)
);

create table function_call (
	id integer primary key autoincrement,
	function int not null,
	time_of_call timestamp not null,
	http_request int not null,
	foreign key(function) references function(id),
	foreign key(http_request) references http_request(id)
);

create table verdict (
	binding int not null,
	verdict int not null,
	time_obtained timestamp not null,
	function_call int not null,
	foreign key(binding) references binding(id),
	foreign key(function_call) references function_call(id),
	primary key(function_call, binding, time_obtained)
);

create table http_request (
	id integer primary key autoincrement,
	time_of_request int not null,
	grouping text not null
);