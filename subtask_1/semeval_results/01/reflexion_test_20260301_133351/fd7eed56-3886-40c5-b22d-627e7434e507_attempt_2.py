% Witness: a lizard
lizard(gecko).

% Rule from premise: All lizards are reptiles
reptile(X) :- lizard(X).

% reptile has NO facts in this model
reptile(_) :- fail.

% Rule from premise: Reptiles are not animals
conflict :- reptile(X), animal(X).

% animal has NO facts in this model
animal(_) :- fail.

% Validity check: Some lizards are not animals
valid_syllogism :- lizard(X), \+ animal(X).