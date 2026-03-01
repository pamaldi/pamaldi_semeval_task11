% Facts (witness to the existence of a novel)
novel(sherlock).

% Rules from premises
book(X) :- novel(X).
edible(X) :- book(X).

% Validity check: All novels are edible
valid_syllogism :- \+ (novel(X), \+ edible(X)).