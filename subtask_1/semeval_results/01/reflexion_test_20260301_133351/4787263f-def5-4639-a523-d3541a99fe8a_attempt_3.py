% Counterexample: dogs are mammals but not animals
dog(fido).
mammal(fido).

% All dogs are mammals (premise)
mammal(X) :- dog(X).

% Validity check: All dogs are animals
valid_syllogism :- dog(X), animal(X).