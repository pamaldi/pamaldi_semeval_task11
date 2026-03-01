% Witness: an animal that is a mammal and non-aquatic
animal(w1).
mammal(w1).
non_aquatic(w1).

% Fail clause for fish (no facts)
fish(_) :- fail.

% A-premise: No non-aquatic animals are fish
conflict :- non_aquatic(X), fish(X).

% A-premise: All mammals are animals
animal(X) :- mammal(X).

% Validity check: Some mammals are not fish
valid_syllogism :- mammal(X), \+ fish(X).