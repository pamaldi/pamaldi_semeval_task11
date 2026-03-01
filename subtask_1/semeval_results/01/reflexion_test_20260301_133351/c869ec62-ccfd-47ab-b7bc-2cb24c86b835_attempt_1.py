% No books are plants (E-premise)
conflict :- book(X), plant(X).

% Every book is an animal (A-premise)
animal(X) :- book(X).

% Fail clauses for empty predicates
book(_) :- fail.
plant(_) :- fail.

% Validity check: conclusion is "Every animal is a plant"
valid_syllogism :- \+ (animal(X), \+ plant(X)).