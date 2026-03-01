% Witness for chair
chair(ch1).

% Rule from first premise: All chairs are tables
table(X) :- chair(X).

% Fail clause for building as it has no facts
building(_) :- fail.

% Rule from second premise: No table is a building
conflict :- table(X), building(X).

% Validity check: No building is a chair
valid_syllogism :- \+ (building(X), chair(X)).