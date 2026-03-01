% COUNTEREXAMPLE: Vehicles exist that are NOT bikes

% Witness: a vehicle that is NOT a bike
vehicle(car1).
% car1 is a vehicle but NOT a bike

% No bikes are cars (E-premise)
% bike/1 has no facts in this model
bike(_) :- fail.
car(_) :- fail.  % No cars exist either

% All bikes are vehicles (A-premise)
vehicle(X) :- bike(X).

% E-premise constraint: No bike is a car
conflict :- bike(X), car(X).

% I-conclusion: Some vehicles are bikes
valid_syllogism :- vehicle(X), bike(X).