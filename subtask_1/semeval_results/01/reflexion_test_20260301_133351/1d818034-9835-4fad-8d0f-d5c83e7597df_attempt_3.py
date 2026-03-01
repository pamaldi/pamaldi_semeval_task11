% Facts for predicates that have instances
organic_compound(sugar1).

% Fail clauses ONLY for predicates with NO facts above
sugar(_) :- fail.
made_of_metal(_) :- fail.

% Rules from premises
organic_compound(X) :- sugar(X).

% E-premise constraint: No organic compound is made of metal
conflict :- organic_compound(X), made_of_metal(X).

% Validity check: No sugar is made of metal (E-conclusion)
valid_syllogism :- \+ (sugar(X), made_of_metal(X)).