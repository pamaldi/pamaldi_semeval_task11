% Facts (witnesses)
cat(fluffy).
pet(fluffy).

% Fail clauses
dog(_) :- fail.

% Rules from premises
% All cats are not dogs (explicitly deny possibility)
conflict :- cat(X), dog(X).

% Validity check (Some pets are not dogs)
valid_syllogism :- pet(X), \+ dog(X).