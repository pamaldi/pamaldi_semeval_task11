% Facts for witness
planet(jupiter).
gas_giant(jupiter).

% Fail clause for predicate with no facts
star(_) :- fail.

% Rule from first premise: No planet is a star.
conflict :- planet(X), star(X).

% Rule from second premise: All gas giants are planets.
planet(X) :- gas_giant(X).

% Validity check for conclusion: Not all gas giants are stars
valid_syllogism :- \+ (gas_giant(X), star(X)).