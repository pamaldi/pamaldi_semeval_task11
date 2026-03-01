% Fail clause for animals that are not trees
animal(X) :- tree(X), fail.

% Witness for plant that is a tree
plant(tree1).
tree(tree1).

% Validity check: at least one plant is an animal
valid_syllogism :- plant(X), animal(X).