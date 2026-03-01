% Facts for I-proposition: Some animals are mammals (witness)
animal(w1).
mammal(w1).

% E-proposition: No mammals are birds
conflict :- mammal(X), bird(X).

% Validity check: Some birds are animals
valid_syllogism :- bird(X), animal(X).