% Facts for counterexample: a bicycle that is NOT a car
bicycle(bmx).
car(merc).

% Rule: Vehicles include every bicycle
vehicle(X) :- bicycle(X).

% Rule: No car is a bicycle
conflict :- car(X), bicycle(X).

% Rule: No bicycle is a car
conflict :- bicycle(X), car(X).

% Validity check: Some vehicle is not a car
valid_syllogism :- vehicle(X), \+ car(X).