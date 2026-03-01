% COUNTEREXAMPLE: A car exists without wheels
car(no_wheels_car).

% Ferrari is a car but we only have one Ferrari with wheels
ferrari(f1).
has_wheels(f1).

% Rule from A-premise: Everything that is a Ferrari is a car
car(X) :- ferrari(X).

% Validity check: Every car has wheels
valid_syllogism :- car(no_wheels_car), \+ has_wheels(no_wheels_car).