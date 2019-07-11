CREATE TABLE function (
    id integer primary key autoincrement,
    fully_qualified_name text not null,
    property text not null,
    foreign key(property) references property(hash)
);
CREATE TABLE property (
    hash text primary key,
    serialised_structure text not null
);
CREATE TABLE binding (
    id integer primary key autoincrement,
    binding_space_index int not null,
    function int not null,
    binding_statement_lines text not null,
    foreign key(function) references function(id)
);
CREATE TABLE function_call (
    id integer primary key autoincrement,
    function int not null,
    time_of_call timestamp not null,
    http_request int not null,
    foreign key(function) references function(id),
    foreign key(http_request) references http_request(id)
);
CREATE TABLE verdict (
    id integer not null primary key autoincrement,
    binding int not null,
    verdict int not null,
    time_obtained timestamp not null,
    function_call int not null,
    collapsing_atom int not null,
    foreign key(binding) references binding(id),
    foreign key(function_call) references function_call(id),
    foreign key(collapsing_atom) references atom(id)
);
CREATE TABLE http_request (
    id integer primary key autoincrement,
    time_of_request int not null,
    grouping text not null
);
CREATE TABLE atom (
    id integer not null primary key autoincrement,
    property_hash text not null,
    serialised_structure text not null,
    index_in_atoms int not null,
    foreign key(property_hash) references property(hash)
);
CREATE TABLE atom_instrumentation_point_pair (
    atom int not null,
    instrumentation_point int not null,
    primary key(atom, instrumentation_point),
    foreign key(atom) references atom(id),
    foreign key(instrumentation_point) references instrumentation_point(id)
);
CREATE TABLE binding_instrumentation_point_pair (
    binding int not null,
    instrumentation_point int not null,
    primary key(binding, instrumentation_point),
    foreign key(binding) references binding(id),
    foreign key(instrumentation_point) references instrumentation_point(id)
);
CREATE TABLE instrumentation_point (
    id integer not null primary key autoincrement,
    serialised_condition_sequence text not null,
    reaching_path_length int not null
);
CREATE TABLE observation (
    id integer not null primary key autoincrement,
    instrumentation_point int not null,
    verdict int not null,
    observed_value text not null,
    atom_index int not null,
    previous_condition integer not null,
    foreign key(previous_condition) references path_condition(id),
    foreign key(instrumentation_point) references instrumentation_point(id),
    foreign key(verdict) references verdict(id)
);
CREATE TABLE observation_assignment_pair (
    observation int not null,
    assignment int not null,
    primary key(observation, assignment),
    foreign key(observation) references observation(id),
    foreign key(assignment) references assignment(id)
);
CREATE TABLE assignment (
    id integer not null primary key autoincrement,
    variable text not null,
    value text not null,
    type text not null
);
CREATE TABLE path_condition_structure (
    id integer not null primary key autoincrement,
    serialised_condition text not null
);
CREATE TABLE path_condition (
    id integer not null primary key autoincrement,
    serialised_condition integer not null,
    next_path_condition integer not null,
    function_call integer not null,
    foreign key(function_call) references function_call(id),
    foreign key(next_path_condition) references path_condition(id)
);
CREATE TABLE search_tree (
    id integer not null primary key autoincrement,
    root_vertex integer not null,
    instrumentation_point integer not null,
    foreign key(root_vertex) references search_tree_vertex(id),
    foreign key(instrumentation_point) references instrumentation_point(id)
);

CREATE TABLE search_tree_vertex (
    id integer not null primary key autoincrement,
    observation integer not null,
    start_of_path integer,
    parent_vertex integer not null,
    foreign key(observation) references observation(id),
    foreign key(start_of_path) references path_condition(id),
    foreign key(parent_vertex) references search_tree_vertex(id)
);