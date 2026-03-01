% Witness: a mammal that is an animal
mammal(cat1).
animal(cat1).

% Rule from premise: All dogs are mammals
mammal(X) :- dog(X).

% Validity check: All dogs are animals
valid_syllogism :- \+ (dog(X), \+ animal(X)).