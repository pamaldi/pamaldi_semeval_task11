% Facts (witness: a bicycle that cannot move)
bicycle(bike1).

% Rules from premises
vehicle(X) :- bicycle(X).

% Validity check: Some vehicle cannot move
valid_syllogism :- vehicle(bike1), \+ move(bike1).