% No elephants are people in kindergarten
conflict :- elephant(X), kindergartener(X).

% All five-year-olds are kindergarteners
kindergartener(X) :- five_year_old(X).

% Fail clauses for empty predicates
elephant(_) :- fail.

% Counterexample witness: a five-year-old who is NOT an elephant
five_year_old(lucy).

% O-conclusion: Some five-year-olds are not elephants
valid_syllogism :- five_year_old(X), \+ elephant(X).