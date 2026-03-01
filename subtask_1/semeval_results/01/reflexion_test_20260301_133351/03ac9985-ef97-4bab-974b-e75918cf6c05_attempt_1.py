% Counterexample: the bicycle IS also a car
bicycle(hybrid).
car(hybrid).

% Rules from A-premises
vehicle(X) :- car(X).
vehicle(X) :- bicycle(X).

% Validity check: No bicycle is a car
valid_syllogism :- \+ (bicycle(X), car(X)).