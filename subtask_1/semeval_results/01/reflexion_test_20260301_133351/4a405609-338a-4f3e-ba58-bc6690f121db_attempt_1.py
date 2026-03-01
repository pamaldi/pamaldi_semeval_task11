% Witness for car (also a fruit)
car(ferrari).
fruit(ferrari).

% No fruit is a vehicle constraint
conflict :- fruit(X), vehicle(X).

% vehicle has no facts and is not implied by anything
vehicle(_) :- fail.

% Validity check: No vehicle is a car → No car is a vehicle (same as \+ (car(X), vehicle(X)))
valid_syllogism :- \+ (car(X), vehicle(X)).