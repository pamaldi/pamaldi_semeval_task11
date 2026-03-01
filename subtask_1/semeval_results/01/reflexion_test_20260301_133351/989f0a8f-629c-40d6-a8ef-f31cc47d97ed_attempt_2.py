% Facts for premises
mammal(bat).
animal(bat).

% Fail clause for insects (since the conclusion asserts insects but the premises don't mention them)
insect(_) :- fail.

% Rule from first premise (No mammal is an insect)
conflict :- mammal(X), insect(X).

% Rule from second premise (Mammals are animals)
animal(X) :- mammal(X).

% Validity check: Some animals are insects
valid_syllogism :- animal(X), insect(X).