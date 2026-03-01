% This syllogism has no I (some S are P) or O (some S are not P) premises
% So no witness facts are needed

% Fail clauses for predicates with no facts
house(_) :- fail.
structure_with_wheels(_) :- fail.

% Rules from premises
structure_with_wheels(X) :- building(X).
building(X) :- house(X).

% Validity check: All houses are structures with wheels
valid_syllogism :- \+ (house(X), \+ structure_with_wheels(X)).