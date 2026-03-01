% COUNTEREXAMPLE: There exists a building that is a chair

% Witness for chair that is a table (I-premise)
chair(t1).
table(t1).

% Fail clause for building to allow negation
building(_) :- fail.

% Rule from second premise: No table is a building
conflict :- table(X), building(X).

% Counterexample: A building that is a chair (makes conclusion false)
building(b1).
chair(b1).

% Validity check: No building is a chair (should fail in this counterexample)
valid_syllogism :- \+ (building(X), chair(X)).