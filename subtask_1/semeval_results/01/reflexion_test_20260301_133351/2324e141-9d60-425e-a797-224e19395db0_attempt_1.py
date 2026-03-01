% Facts for witness: an entity that is a planet
planet(earth).

% Rules from premises
celestial_body(X) :- planet(X).
round_object(X) :- planet(X).

% Validity check: Some round objects are celestial bodies
valid_syllogism :- round_object(X), celestial_body(X).