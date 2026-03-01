% Facts: an example of a rock that is a feline
rock(whiskers).
feline(whiskers).

% animal has no facts, so define it as not existing
animal(_) :- fail.

% rock cannot be animal
conflict :- rock(X), animal(X).

% Validity check: Some felines are not animals
valid_syllogism :- feline(X), \+ animal(X).