% COUNTEREXAMPLE: Build a world where premises are true but conclusion is false

% Witnesses for cities that are NOT government seats
city(newtown).

% government_seat has NO facts
government_seat(_) :- fail.

% E-premise: No state is a government seat
conflict :- state(X), government_seat(X).

% I-premise: Some cities are not government seats (newtown is a city not a government seat)
% Already satisfied by newtown

% Counterexample: newtown is a city but NOT a state
% (contrary to the conclusion "All cities are states")
city(newtown).

% Some cities are not states
% (This makes the conclusion false)
% newtown is a city that is NOT a state
\+ state(newtown).

% Validity check: Does the conclusion hold? It should NOT
% The conclusion "All cities are states" would require: city(X) → state(X)
% But we have newtown as a city that is NOT a state
valid_syllogism :- city(X), state(X).