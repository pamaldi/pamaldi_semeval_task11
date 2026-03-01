% Facts: a star that is not a celestial body (counterexample entity)
star(sol).
% No star is a planet
planet(_) :- fail.

% Rules from premises
celestial_body(X) :- planet(X).
conflict :- planet(X), star(X).

% Validity check for conclusion: Some stars are not celestial bodies
valid_syllogism :- star(X), \+ celestial_body(X).