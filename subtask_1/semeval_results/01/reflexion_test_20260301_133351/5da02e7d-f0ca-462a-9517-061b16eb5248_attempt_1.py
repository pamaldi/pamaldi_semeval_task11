% Facts for eagles that are birds
eagle(hawk1).
bird(hawk1).

% No mammal is an eagle
mammal(_) :- fail.

% Some birds are not mammals (eagle is a bird but not a mammal)
valid_syllogism :- bird(X), \+ mammal(X).