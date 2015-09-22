-- WARNING. this sql is executed EVERY start

CREATE TABLE if not exists cards (
id integer primary key,
uid CHAR(128), 
vorname TEXT not null,
nachname TEXT not null,
units int, 
active int 
);

CREATE TABLE if not exists log (
  log_ts DATETIME DEFAULT CURRENT_TIMESTAMP,
  card_id integer NOT NULL,
  log_event integer NOT NULL,
  log_arg integer
);

-- log_event == 0 : Login
-- log_event == 1 : Logout arg=number of seconds
