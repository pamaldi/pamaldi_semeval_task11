% I-premise witness: a plant that is a living thing
plant(plant1).
living_thing(plant1).

% I-premise witness: a tree that is a plant
tree(tree1).
plant(tree1).

% Validity check: Does every tree have to be a living thing?
% Counterexample: tree that is NOT a living thing (violates the conclusion)
valid_syllogism :- tree(X), \+ living_thing(X).