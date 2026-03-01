% Counterexample: a flower that is also a plant but not a tree
flower(rose).
plant(rose).

% Rules from premises
plant(X) :- tree(X).
plant(X) :- flower(X).

% Validity check: Some flowers are not trees
valid_syllogism :- flower(X), \+ tree(X).