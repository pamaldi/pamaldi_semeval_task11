% No furniture is a planet
planet(_) :- fail.

% All chairs are furniture
furniture(X) :- chair(X).

% Witness chair
chair(library_chair).

% Validity check: No chair is a planet
valid_syllogism :- \+ (chair(X), planet(X)).