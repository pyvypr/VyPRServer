create table event (
    id integer primary key,
    type text not null,
    action_to_perform text not null,
    data text not null,
    time_added datetime not null
);