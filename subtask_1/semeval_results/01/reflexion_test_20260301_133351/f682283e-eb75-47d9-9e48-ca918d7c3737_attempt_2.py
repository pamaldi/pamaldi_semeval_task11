% Counterexample: entities exist that make premises true but conclusion false
% We'll make animals and plants disjoint sets

% Create a plant that is NOT an animal
plant(tree1).
tree(tree1).

% Create an animal that is NOT a plant
animal(dog1).

% No trees exist that are animals (E-premise: No animal is a tree)
conflict :- animal(X), tree(X).

% All trees are plants (A-premise: All trees are plants)
plant(X) :- tree(X).

% Validity check: Some plants are animals (I-conclusion)
% This should FAIL to show the syllogism is INVALID
valid_syllogism :- plant(X), animal(X).