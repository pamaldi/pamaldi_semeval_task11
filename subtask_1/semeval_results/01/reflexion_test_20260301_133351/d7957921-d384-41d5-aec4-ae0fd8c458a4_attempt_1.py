% Facts for the I-premise: Some animals are fish
animal(f1).
fish(f1).

% Fail clause for window (no facts and no rules)
window(_) :- fail.

% E-premise constraint: No fish is a window
conflict :- fish(X), window(X).

% Validity check: Some animals are windows
valid_syllogism :- animal(X), window(X).