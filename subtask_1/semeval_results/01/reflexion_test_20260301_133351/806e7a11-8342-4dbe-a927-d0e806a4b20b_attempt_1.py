% Fail clause for mammals since no fish is a mammal
mammal(_) :- fail.

% Witness: a reptile that is a fish
reptile(trout).
fish(trout).

% Rule from first premise: No fish is a mammal
conflict :- fish(X), mammal(X).

% Rule from second premise: Some reptiles are fish
fish(X) :- reptile(X), fish(X).

% Validity check: Some reptiles are mammals
valid_syllogism :- reptile(X), mammal(X).