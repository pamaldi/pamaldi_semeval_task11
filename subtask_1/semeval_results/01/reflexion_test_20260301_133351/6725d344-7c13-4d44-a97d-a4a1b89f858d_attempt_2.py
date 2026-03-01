% Facts for witness: a planet (which is NOT a celestial body)
planet(earth).

% star is undefined (no facts)
% celestial_body is undefined (no facts)

% Fail clauses for predicates with no facts
star(_) :- fail.
celestial_body(_) :- fail.

% Premise 1: No planet is a celestial body
% Premise 2: No planet is a star
% These are both E-statements
conflict :- planet(X), celestial_body(X).
conflict :- planet(X), star(X).

% Validity check for conclusion: Some stars are not celestial bodies
% This is an O-type statement
valid_syllogism :- star(X), \+ celestial_body(X).