% Facts for I-premise (some cars are not expensive)
car(c1).
\+ expensive(c1).

% A-premise: All cars are vehicles
vehicle(X) :- car(X).

% Validity check: Some vehicles are expensive
valid_syllogism :- vehicle(X), expensive(X).