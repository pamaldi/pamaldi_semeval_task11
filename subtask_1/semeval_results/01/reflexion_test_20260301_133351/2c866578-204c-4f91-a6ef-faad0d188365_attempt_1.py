% Witness: a Ferrari that has wheels
ferrari(f1).
has_wheels(f1).

% Rule from A-premise: Everything that is a Ferrari is a car
car(X) :- ferrari(X).

% Validity check: Every car has wheels
valid_syllogism :- \+ (car(X), \+ has_wheels(X)).