% Facts for "A portion of all paper is a book" (Some paper is book)
% We need a witness that is both paper and book
paper(witness1).  
book(witness1).

% Fail clause for "There is not a single piece of paper that can be eaten" (No paper is edible)
edible(_) :- fail.

% Validity check for the conclusion "Some books are edible"
valid_syllogism :- book(X), edible(X).