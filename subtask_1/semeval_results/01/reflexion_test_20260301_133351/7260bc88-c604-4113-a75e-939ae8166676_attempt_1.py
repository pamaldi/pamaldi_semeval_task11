% Facts (witnesses)
dog(buddy).
mammal(buddy).

% Fail clause for empty predicate
feathered_animal(_) :- fail.

% Rules from premises
% No mammal is a feathered_animal
conflict :- mammal(X), feathered_animal(X).

% A portion of dogs are mammals (already asserted by dog(buddy), mammal(buddy))

% Validity check: Some dogs are not feathered_animals
valid_syllogism :- dog(X), \+ feathered_animal(X).