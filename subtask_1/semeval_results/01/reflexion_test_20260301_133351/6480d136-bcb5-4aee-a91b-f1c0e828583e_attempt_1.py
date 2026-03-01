% Facts
cat(tom).
feline(tom).

% Rules
feline(X) :- cat(X).

% Mammal and feline have no overlap - no mammal is a feline and no feline is a mammal
mammal(_) :- fail.
feline(X) :- \+ mammal(X).

% Validity check: No cat is a mammal
valid_syllogism :- cat(X), \+ mammal(X).