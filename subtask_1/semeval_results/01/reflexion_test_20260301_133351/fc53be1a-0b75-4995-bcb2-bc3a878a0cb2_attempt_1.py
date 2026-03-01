% Feline has NO facts in this model
feline(_) :- fail.

% House pet has NO facts in this model
house_pet(_) :- fail.

% Rule from first premise: No house pet is a feline
conflict :- house_pet(X), feline(X).

% Rule from second premise: No cat is a house pet
conflict :- cat(X), house_pet(X).

% Witness for conclusion: A cat exists that is NOT a feline
cat(coco).

% O-conclusion: Some cats are not felines
valid_syllogism :- cat(X), \+ feline(X).