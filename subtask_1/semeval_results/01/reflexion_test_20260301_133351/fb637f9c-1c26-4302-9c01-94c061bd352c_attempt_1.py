% Facts for the categories
chair(table1).
living(whiskers).

% Fail clauses for empty predicates
inanimate(_) :- fail.
% No fail clause for chair/1 since it has facts
% No fail clause for living/1 since it has facts
% No fail clause for inanimate/1 because we defined a fail clause

% Rules from premises
% "The category of chairs and the category of living things do not overlap."
conflict :- chair(X), living(X).

% "The group of living things and the group of inanimate objects are mutually exclusive."
conflict :- living(X), inanimate(X).

% "A portion of inanimate objects are not chairs." 
% Counterexample: an inanimate object that is NOT a chair
inanimate(floor1).

% Validity check: Some inanimate object is not a chair
valid_syllogism :- inanimate(X), \+ chair(X).