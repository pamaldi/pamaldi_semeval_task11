% Facts for cars (counterexample entity)
car(ford).

% object has NO facts, so we need a fail clause for it
object(_) :- fail.

% Rule from first A-premise: All vehicles are objects
object(X) :- vehicle(X).

% Validity check for E-conclusion: No car is a vehicle
valid_syllogism :- \+ (car(X), vehicle(X)).