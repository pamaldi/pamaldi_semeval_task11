% COUNTEREXAMPLE: All flowers are also trees
flower(rose).
tree(rose).

% plant is derived from both tree and flower
plant(X) :- tree(X).
plant(X) :- flower(X).

% Validity check: Some flowers are not trees (should FAIL)
valid_syllogism :- flower(X), \+ tree(X).