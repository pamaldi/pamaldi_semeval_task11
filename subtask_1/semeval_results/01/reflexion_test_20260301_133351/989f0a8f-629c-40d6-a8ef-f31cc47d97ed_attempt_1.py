% Fail clause for mammals who are insects
mammal_insect(_) :- fail.

% Witness for mammals who are animals
animal(bat).
mammal(bat).

% Rule from first premise (No mammal is an insect)
conflict :- mammal(X), insect(X).

% Rule from second premise (Mammals are animals)
animal(X) :- mammal(X).

% Validity check: Some animals are insects
valid_syllogism :- animal(X), insect(X).