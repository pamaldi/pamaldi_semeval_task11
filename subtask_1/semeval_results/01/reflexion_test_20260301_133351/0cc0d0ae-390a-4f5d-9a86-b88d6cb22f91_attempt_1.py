% Facts for witnesses
chair(c1).
table(t1).

% Fail clause for items designed for sitting (no facts)
designed_for_sitting(_) :- fail.

% A-premise: Items that are tables are in no way items designed for sitting
conflict :- table(X), designed_for_sitting(X).

% A-premise: Everything that is a chair is an item designed for sitting
designed_for_sitting(X) :- chair(X).

% Validity check: No chair is a table
valid_syllogism :- \+ (chair(X), table(X)).