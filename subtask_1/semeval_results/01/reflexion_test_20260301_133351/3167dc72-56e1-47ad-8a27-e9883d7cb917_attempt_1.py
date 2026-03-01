% Fail clause for aquatic_animal to ensure none are true
aquatic_animal(_) :- fail.

% Fail clause for bird_aquatic to enforce no bird is aquatic
conflict :- bird(X), aquatic_animal(X).

% Witness: an animal that is a bird
animal(sparrow).
bird(sparrow).

% Validity check: Some animals are aquatic animals
valid_syllogism :- animal(X), aquatic_animal(X).