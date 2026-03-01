% Facts for cars (counterexample entity)
car(ford).

% vehicle has NO facts, so we need a fail clause for it
vehicle(_) :- fail.

% Rules from A-premise: All vehicles are objects
object(X) :- vehicle(X).

% E-premise: No cars are objects
object(_) :- fail.

% Validity check for E-conclusion: No car is a vehicle
valid_syllogism :- \+ (car(X), vehicle(X)).