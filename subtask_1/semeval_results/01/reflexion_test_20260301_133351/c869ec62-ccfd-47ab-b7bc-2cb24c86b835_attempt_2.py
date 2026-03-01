% Facts for books, plants (no facts), and animals
book(b1).
book(b2).

% No books are plants (E-premise)
conflict :- book(X), plant(X).

% Every book is an animal (A-premise)
animal(X) :- book(X).

% Validity check: conclusion is "Every animal is a plant"
valid_syllogism :- \+ (animal(X), \+ plant(X)).