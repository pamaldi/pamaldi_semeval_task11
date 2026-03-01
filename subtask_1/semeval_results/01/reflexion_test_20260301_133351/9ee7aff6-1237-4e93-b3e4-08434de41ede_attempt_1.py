% Premise 1: No canine is a feline
conflict :- canine(X), feline(X).

% Premise 2: Everything that is a canine is also a dog
dog(X) :- canine(X).

% Conclusion: All dogs are cats
% To test validity, we try to find a dog that is NOT a cat
valid_syllogism :- \+ (dog(X), \+ cat(X)).

% Fail clauses
feline(_) :- fail.
canine(_) :- fail.
cat(_) :- fail.