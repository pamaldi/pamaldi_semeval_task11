% Facts for pencils and books
pencil(pencil1).
book(book1).

% Fail clause for paper_good if no facts exist
paper_good(_) :- fail.

% E-premise: No pencil is a paper good (via conflict)
conflict :- pencil(pencil1), paper_good(pencil1).

% E-premise: No pencil is a book (via conflict)
conflict :- pencil(pencil1), book(pencil1).

% A-conclusion: All books are paper goods
valid_syllogism :- \+ (book(book1), \+ paper_good(book1)).