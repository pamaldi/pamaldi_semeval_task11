% Facts for predicates that have instances
planet(earth).

% Fail clauses for predicates with NO facts
celestial_object(_) :- fail.

% Rules from premises
organic_thing(X) :- planet(X).
conflict :- organic_thing(X), celestial_object(X).

% Validity check
valid_syllogism :- \+ (planet(X), celestial_object(X)).