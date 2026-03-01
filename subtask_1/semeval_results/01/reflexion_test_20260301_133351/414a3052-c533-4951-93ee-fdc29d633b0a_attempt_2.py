% Facts for I-proposition: Some animals are mammals (witness)
animal(w1).
mammal(w1).

% E-proposition: No mammals are birds
conflict :- mammal(X), bird(X).

% Fail clause for bird/1 since it has no facts
bird(_) :- fail.

% Validity check: Some birds are animals
valid_syllogism :- bird(X), animal(X).