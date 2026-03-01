% E-premise: No horse is alive
% Counterexample: horses are NOT alive
horse(claymore).

% horse is NOT alive (fact), so we don't need a fail clause
% alive has no facts, and no rules (for now)
alive(_) :- fail.

% A-premise: No car is not alive → All cars are alive
% Encode as: If something is a car, it must be alive
car(X) :- alive(X).

% I-conclusion: Some horses are cars
valid_syllogism :- horse(X), car(X).