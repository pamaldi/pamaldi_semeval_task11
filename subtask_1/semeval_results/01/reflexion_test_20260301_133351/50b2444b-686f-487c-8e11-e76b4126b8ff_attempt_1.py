% Facts (witnesses or counterexample entities)
book(paperbook1).
edible(paperbook1).

% Fail clause for edible (only if no facts exist for it, but here we have one)
% Not needed, since edible(paperbook1) exists

% Fail clause for eatable_paper/1 - since no paper is edible
eatable_paper(_) :- fail.

% Rule from "A portion of all paper is a book" (Some paper is book)
% No rule needed since we already have a fact for book(paperbook1)

% Validity check for "Some books are edible"
valid_syllogism :- book(X), edible(X).