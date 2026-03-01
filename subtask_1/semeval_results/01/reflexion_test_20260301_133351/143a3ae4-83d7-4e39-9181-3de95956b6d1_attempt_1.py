% Facts for pets (no animals are pets)
pet(_) :- fail.

% All dogs are pets
pet(X) :- dog(X).

% Witness for a dog (to test the conclusion)
dog(buddy).

% Validity check: Some dogs are not animals
valid_syllogism :- dog(X), \+ animal(X).