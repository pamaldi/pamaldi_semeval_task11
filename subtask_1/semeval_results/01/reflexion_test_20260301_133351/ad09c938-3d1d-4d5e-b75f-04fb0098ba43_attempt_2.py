% Facts for books that do not have pages
book(book1).

% All books are living things
living_thing(X) :- book(X).

% Validity check: Some living things have pages
valid_syllogism :- living_thing(X), pages(X).