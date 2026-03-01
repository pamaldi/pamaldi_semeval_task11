% Facts to build a counterexample
lizard(dragon1).
dog(dragon1).

% No dogs are felines
feline(_) :- fail.
conflict :- dog(X), feline(X).

% Validity check: Some felines are lizards
valid_syllogism :- feline(X), lizard(X).