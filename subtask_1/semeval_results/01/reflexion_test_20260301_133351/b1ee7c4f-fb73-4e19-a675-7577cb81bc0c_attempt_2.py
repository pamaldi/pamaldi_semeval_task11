% I-premise 1 witness: a plant that is a living thing
plant(plant1).
living_thing(plant1).

% I-premise 2 witness: a tree that is a plant
tree(tree1).
plant(tree1).

% Counterexample: a tree that is NOT a living thing (this will make the conclusion false)
tree(tree2).
% No need to assert tree2 is a plant (the premise only requires "some trees are plants")
% No need to assert living_thing(tree2) will make the conclusion false

% Validity check: Does the conclusion hold? (A-type: "Every tree is a living thing")
% This should FAIL to show syllogism is INVALID
valid_syllogism :- tree(X), \+ living_thing(X).