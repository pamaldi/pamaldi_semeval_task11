% Facts
cat(tom).
canine(buddy).

% Rules from premises
feline(X) :- cat(X).
conflict :- feline(X), canine(X).

% Validity check: Some canines are not cats (O-conclusion)
valid_syllogism :- canine(X), \+ cat(X).