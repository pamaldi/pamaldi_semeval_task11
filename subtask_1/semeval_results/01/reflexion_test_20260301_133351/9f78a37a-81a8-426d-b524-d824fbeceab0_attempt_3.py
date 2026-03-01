% Facts
apple(a1).

% Fail clauses for predicates with no instances
banana(_) :- fail.

% Rules from premises
fruit(X) :- apple(X).

% E-premise constraint
conflict :- banana(X), apple(X).

% Validity check (A-conclusion: All bananas are fruits)
valid_syllogism :- \+ (banana(X), \+ fruit(X)).