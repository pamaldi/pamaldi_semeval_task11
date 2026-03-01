% Counterexample: an animal that is a vehicle (e.g., a horse)
animal(horse1).
vehicle(horse1).

% A-premise: All cars are vehicles
vehicle(X) :- car(X).

% E-premise: No animal is a car
conflict :- animal(X), car(X).

% E-conclusion: No animal is a vehicle
valid_syllogism :- \+ (animal(X), vehicle(X)).