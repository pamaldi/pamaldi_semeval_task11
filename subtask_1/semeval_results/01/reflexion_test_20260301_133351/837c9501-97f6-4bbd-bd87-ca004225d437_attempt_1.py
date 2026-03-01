% Facts (witnesses or counterexample entities)
earth(earth1).

% planet has no facts directly because it is defined via rules
% star has no facts and no rules, so it must use fail clause
star(_) :- fail.

% Rules from premises
planet(X) :- earth(X).

% Validity check: Some things on Earth are stars
valid_syllogism :- earth(X), star(X).