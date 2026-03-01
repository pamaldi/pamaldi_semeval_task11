% Facts
cat(some_cat).

% Fail clauses for predicates with no instances
fish(_) :- fail.

% Rules
% "There are no fish that do not live on the moon" → All fish live on the moon
on_moon(X) :- fish(X).

% "No cat is a fish"
conflict :- cat(X), fish(X).

% Validity check: "At least some cats live on the moon"
valid_syllogism :- cat(X), on_moon(X).