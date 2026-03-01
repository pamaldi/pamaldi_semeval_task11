% COUNTEREXAMPLE: All penguins are birds, and some animals are birds.
% This satisfies the premises but makes the conclusion FALSE.

% Some animals are birds (I-type)
animal(bird1).
bird(bird1).

% Some penguins are animals (I-type)
penguin(pingu).
animal(pingu).

% All penguins are birds (This makes the conclusion FALSE)
bird(X) :- penguin(X).

% Validity check: Some penguin is NOT a bird (This should FAIL)
valid_syllogism :- penguin(X), \+ bird(X).