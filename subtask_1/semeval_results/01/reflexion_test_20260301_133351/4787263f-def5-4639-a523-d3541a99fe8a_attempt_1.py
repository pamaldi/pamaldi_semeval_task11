% I-premise witness: Some mammal is an animal
mammal(bear).
animal(bear).

% A-premise: All dogs are mammals
mammal(X) :- dog(X).

% Validity check: All dogs are animals
valid_syllogism :- \+ (dog(X), \+ animal(X)).