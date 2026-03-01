% I-premise 1 witness: a plant that is a living thing
plant(living_plant1).
living_thing(living_plant1).

% I-premise 2 witness: a tree that is a plant
tree(non_living_tree1).
plant(non_living_tree1).

% Counterexample: a tree that is NOT a living thing
% (This will make the conclusion "Every tree is a living thing" FALSE)
% No need to assert living_thing(non_living_tree1)

% Validity check: Does the conclusion hold? (A-type: "Every tree is a living thing")
% This should FAIL to show syllogism is INVALID
valid_syllogism :- tree(X), \+ living_thing(X).