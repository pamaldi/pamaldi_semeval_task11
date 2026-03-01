% Facts for books and animals
book(b1).
book(b2).
animal(b1).
animal(b2).

% No books are plants (E-premise)
conflict :- book(X), plant(X).

% Every book is an animal (A-premise)
animal(X) :- book(X).

% plant/1 has no facts, no rules - use fail clause
plant(_) :- fail.

% Validity check: conclusion is "Every animal is a plant"
valid_syllogism :- \+ (animal(X), \+ plant(X)).