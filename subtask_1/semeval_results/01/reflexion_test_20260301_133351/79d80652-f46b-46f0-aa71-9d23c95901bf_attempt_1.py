% Witness: a paper object that is a book
paper_object(book1).
book(book1).

% Witness: a notebook that is a paper object
notebook(note1).
paper_object(note1).

% Witness: a notebook that is NOT a book
notebook(note2).
paper_object(note2).

% A portion of paper objects are books
book(X) :- paper_object(X).

% Some notebooks are paper objects
paper_object(X) :- notebook(X).

% Not all notebooks are books (counterexample: note2 is a notebook but not a book)
valid_syllogism :- notebook(X), \+ book(X).