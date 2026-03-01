% Witnesses for I-premise: Some doctor wears a uniform
doctor(john).
uniform(john).

% Rules from E-premise: No bus driver wears a uniform
uniform(X) :- fail.  % Uniform has facts, so this is invalid and must be removed
conflict :- bus_driver(X), uniform(X).

% Rules from conclusion: Some doctor is a bus driver
bus_driver(john).

% Check conclusion: Some doctor is a bus driver
valid_syllogism :- doctor(X), bus_driver(X).