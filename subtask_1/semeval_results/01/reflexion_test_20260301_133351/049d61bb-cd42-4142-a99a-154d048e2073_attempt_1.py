% Facts for I-proposition (Some cars are fish)
car(f1).
fish(f1).

% Rules for E-proposition (All fish are swimmers)
swimmer(X) :- fish(X).

% Validity check for I-conclusion (Some swimmers are cars)
valid_syllogism :- swimmer(X), car(X).