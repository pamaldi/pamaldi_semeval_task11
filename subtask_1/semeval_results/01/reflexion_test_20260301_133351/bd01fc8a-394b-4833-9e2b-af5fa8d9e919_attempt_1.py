% Witnesses for cities that are NOT government seats
city(newtown).
\+ government_seat(newtown).

% government_seat has NO facts, so we need fail clause
government_seat(_) :- fail.

% E-premise constraint: No state is a government seat
conflict :- state(X), government_seat(X).

% I-premise: Some cities are not government seats
% Already satisfied by newtown

% Rule from conclusion: All cities are states
state(X) :- city(X).

% Validity check: No city is a government seat (premise), but all cities are states (conclusion)
valid_syllogism :- city(X), state(X), \+ government_seat(X).