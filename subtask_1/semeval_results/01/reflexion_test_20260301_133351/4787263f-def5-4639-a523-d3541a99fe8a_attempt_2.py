% I-premise witness: Some mammals are animals
mammal(bear).
animal(bear).

% A-premise: All dogs are mammals
dog(fido).
mammal(X) :- dog(X).

% Validity check: All dogs are animals
animal(X) :- dog(X).
valid_syllogism :- \+ (dog(X), \+ animal(X)).