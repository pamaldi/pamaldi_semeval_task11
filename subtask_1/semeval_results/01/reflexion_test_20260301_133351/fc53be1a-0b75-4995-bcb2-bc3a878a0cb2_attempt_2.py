% This syllogism is INVALID - Two negative premises cannot produce a valid conclusion

% Feline has NO facts in this model (not distributed in conclusion)
feline(_) :- fail.

% House pet has NO facts in this model (middle term)
house_pet(_) :- fail.

% Rule from first premise: No house pet is a feline
conflict :- house_pet(X), feline(X).

% Rule from second premise: No cat is a house pet
conflict :- cat(X), house_pet(X).

% COUNTEREXAMPLE: Cat is also a feline
cat(einstein).
feline(einstein).

% O-conclusion check: Some cats are not felines
valid_syllogism :- cat(X), \+ feline(X).