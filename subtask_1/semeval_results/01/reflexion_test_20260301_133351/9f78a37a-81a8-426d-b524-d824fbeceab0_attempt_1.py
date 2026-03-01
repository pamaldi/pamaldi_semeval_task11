% Facts
apple(a1).

% Rules from premises
fruit(X) :- apple(X).

% E-premise constraint
conflict :- banana(X), apple(X).

% Validity check
valid_syllogism :- \+ (banana(X), \+ fruit(X)).