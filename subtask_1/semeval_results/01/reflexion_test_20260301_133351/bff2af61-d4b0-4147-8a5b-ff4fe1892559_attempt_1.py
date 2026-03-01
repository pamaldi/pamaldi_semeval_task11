% Facts for bikes
bike(bike1).

% Rules for premises
vehicle(X) :- bike(X).

% Fail clause for cars since it has no facts
car(_) :- fail.

% E-premise constraint: No bike is a car
conflict :- bike(X), car(X).

% I-conclusion: Some vehicle is a bike
valid_syllogism :- vehicle(X), bike(X).