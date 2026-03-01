% Facts for predicates that have instances
flower(rose).
plant(rose).

% Predicates with no facts (use fail clause)
tree(_) :- fail.

% Rules from premises
plant(X) :- tree(X).
plant(X) :- flower(X).

% Validity check: Some flowers are not trees
valid_syllogism :- flower(X), \+ tree(X).