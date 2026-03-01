% Fail clauses for predicates with no facts
shrubs(_) :- fail.
tall_plant(_) :- fail.

% Rule from E-premise: No shrubs are tall plants
conflict :- shrubs(X), tall_plant(X).

% Rule from A-premise: All trees are tall plants
tall_plant(X) :- tree(X).

% Counterexample: a tree that is NOT a shrub
tree(oak1).

% O-conclusion: Some trees are not shrubs
valid_syllogism :- tree(X), \+ shrubs(X).