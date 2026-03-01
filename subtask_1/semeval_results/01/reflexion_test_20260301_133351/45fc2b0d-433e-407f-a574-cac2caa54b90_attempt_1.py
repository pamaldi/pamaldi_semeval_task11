% Facts (witnesses or counterexample entities)
comet(halley).

% Fail clauses ONLY for predicates with NO facts and NO rules
celestial_body(_) :- fail.

% Rules from premises
celestial_body(X) :- planet(X).
planet(X) :- comet(X).

% Validity check
valid_syllogism :- comet(X), celestial_body(X).