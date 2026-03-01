% Witness for shoe (which is also an idea and insect)
shoe(s1).

% Rules from premises
idea(X) :- shoe(X).
insect(X) :- idea(X).

% Validity check: Some insects are shoes
valid_syllogism :- insect(X), shoe(X).