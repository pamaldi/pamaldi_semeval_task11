% Facts (witness for "Some things made of cheese are stars")
dog(biscuit).
star(biscuit).
made_of_cheese(biscuit).

% Rule from first premise: All dogs are stars
star(X) :- dog(X).

% Rule from second premise: All dogs are made of cheese
made_of_cheese(X) :- dog(X).

% Validity check: Some things made of cheese are stars
valid_syllogism :- made_of_cheese(X), star(X).