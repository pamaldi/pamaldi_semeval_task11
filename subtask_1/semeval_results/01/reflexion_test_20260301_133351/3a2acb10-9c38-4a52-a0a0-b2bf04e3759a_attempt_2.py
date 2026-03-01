% Witness: a car that is NOT a truck (establishing "Not all cars are trucks")
car(charger).

% All cars are vehicles
vehicle(X) :- car(X).

% Validity check: Some vehicle is not a truck
valid_syllogism :- vehicle(X), \+ truck(X).