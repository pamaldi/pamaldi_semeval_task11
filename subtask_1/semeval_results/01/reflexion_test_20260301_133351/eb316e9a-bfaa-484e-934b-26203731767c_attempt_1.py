% Witness: Earth is a planet
celestial_body(earth1).
planet(earth1).

% star has NO facts, so we need fail clause
star(_) :- fail.

% E-premise constraint: No planet is a star
conflict :- planet(X), star(X).

% Rule from A-premise: Every Earth is a planet
planet(X) :- celestial_body(X), earth(X).
earth(earth1).

% O-conclusion: Some Earth is not a star
valid_syllogism :- earth(X), \+ star(X).