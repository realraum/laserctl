DROP TABLE cards;

CREATE TABLE cards(
id integer primary key,
uid CHAR(128), 
vorname TEXT not null,
nachname TEXT not null,
units int, 
active int 
);

