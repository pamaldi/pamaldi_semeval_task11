% Counterexample: entities exist that break the conclusion
plant(animal_plant).   % This plant is also an animal
animal(animal_plant).  % This animal is also a plant

% Fail clause for trees (no trees exist)
tree(_) :- fail.

% Rule from first premise: No animal is a tree
conflict :- animal(X), tree(X).

% Rule from second premise: All trees are plants
plant(X) :- tree(X).

% Validity check: Some plants are animals
valid_syllogism :- plant(X), animal(X).