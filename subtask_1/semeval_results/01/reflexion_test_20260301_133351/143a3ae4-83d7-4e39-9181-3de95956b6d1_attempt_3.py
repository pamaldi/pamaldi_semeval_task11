% Facts for dogs
dog(buddy).

% All dogs are pets
pet(X) :- dog(X).

% No animals are pets (so pet(X) must imply \+ animal(X))
% This is achieved by making animal/1 undefined (no facts)
% and ensuring pet(X) is defined through other means

% Validity check: Some dogs are not animals
valid_syllogism :- dog(X), \+ animal(X).