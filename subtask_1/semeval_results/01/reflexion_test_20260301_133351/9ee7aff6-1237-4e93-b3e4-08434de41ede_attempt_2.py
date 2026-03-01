% Case A: We construct a counterexample to show the syllogism is INVALID

% Premise 1: No canine is a feline (E-type)
conflict :- canine(X), feline(X).

% Premise 2: Everything that is a canine is also a dog (A-type)
dog(X) :- canine(X).

% Counterexample: A dog that is NOT a cat
dog(rex).
% Do NOT assert cat(rex) to make the conclusion false

% Fail clauses for undefined terms in this model
feline(_) :- fail.
canine(_) :- fail.

% Check: All dogs are cats? (Should FAIL to show INVALID syllogism)
valid_syllogism :- \+ (dog(X), \+ cat(X)).