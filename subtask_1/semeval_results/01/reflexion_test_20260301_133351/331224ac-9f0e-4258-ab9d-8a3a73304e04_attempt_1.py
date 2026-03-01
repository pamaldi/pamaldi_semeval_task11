% Entities without facts
aquatic_mammal(_) :- fail.
fish(_) :- fail.
animal_with_wings(_) :- fail.

% Rules from premises
fish(X) :- aquatic_mammal(X).
conflict :- aquatic_mammal(X), animal_with_wings(X).

% Validity check: No fish are animals with wings
valid_syllogism :- \+ (fish(X), animal_with_wings(X)).