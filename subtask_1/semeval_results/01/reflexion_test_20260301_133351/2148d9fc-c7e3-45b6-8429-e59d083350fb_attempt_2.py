% Facts (witness for parts of year that are days)
part_of_year(jan1).
day(jan1).

% month has NO facts in this model
month(_) :- fail.

% Rules from premises
day(X) :- part_of_year(X).

% E-premise constraint
conflict :- month(X), day(X).

% O-conclusion: Some months are not parts of the year
valid_syllogism :- month(X), \+ part_of_year(X).