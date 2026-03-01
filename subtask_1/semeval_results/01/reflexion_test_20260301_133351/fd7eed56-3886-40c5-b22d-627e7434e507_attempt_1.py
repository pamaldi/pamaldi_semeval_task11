% Witness: a lizard
lizard(gecko).

% Rule from premise: All lizards are reptiles
reptile(X) :- lizard(X).

% Rule from premise: Reptiles are not animals
conflict :- reptile(X), animal(X).

% Validity check: Some lizards are not animals
valid_syllogism :- lizard(X), \+ animal(X).