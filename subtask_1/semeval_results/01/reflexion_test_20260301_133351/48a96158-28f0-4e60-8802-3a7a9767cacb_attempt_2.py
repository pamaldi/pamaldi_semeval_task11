% Facts: some mammals are animals (witness: cat1)
mammal(cat1).
animal(cat1).

% Rule from premise: All dogs are mammals
dog(rover).
mammal(X) :- dog(X).

% Validity check: All dogs are animals
valid_syllogism :- \+ (dog(X), \+ animal(X)).