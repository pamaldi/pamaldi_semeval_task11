% Every sugar is an organic compound (A-premise)
organic_compound(X) :- sugar(X).

% No organic compound is made of metal (E-premise)
conflict :- organic_compound(X), made_of_metal(X).

% Validity check: No sugar is made of metal (E-conclusion)
valid_syllogism :- \+ (sugar(X), made_of_metal(X)).

% Fail clauses for predicates with no facts
made_of_metal(_) :- fail.