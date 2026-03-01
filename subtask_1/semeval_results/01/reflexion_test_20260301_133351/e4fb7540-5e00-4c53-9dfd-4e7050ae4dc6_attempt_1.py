% Facts for entities in the counterexample
animal(dog1).
chair(dog1).
chair(chair1).

% No furniture is an animal
furniture(_) :- fail.

% Rule from premise: Every animal is a chair
chair(X) :- animal(X).

% E-premise constraint: No furniture is an animal
conflict :- furniture(X), animal(X).

% Validity check: Some chairs are not furniture
valid_syllogism :- chair(X), \+ furniture(X).