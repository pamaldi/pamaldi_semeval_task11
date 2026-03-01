% Witness: reptile that is also a mammal
reptile(lizard).
mammal(lizard).

% Fish has no facts (nothing is fish)
fish(_) :- fail.

% E-premise: no mammals are fish
conflict :- mammal(X), fish(X).

% Validity check: some fish are reptiles
valid_syllogism :- fish(X), reptile(X).