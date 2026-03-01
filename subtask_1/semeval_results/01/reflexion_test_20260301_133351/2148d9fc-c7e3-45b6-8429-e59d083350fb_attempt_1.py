% Facts (witnesses for parts of year that are days)
day(jan1).
part_of_year(jan1).

% month has NO facts in this model
month(_) :- fail.

% Rules from premises
part_of_year(X) :- day(X).

% E-premise constraint
conflict :- month(X), day(X).

% O-conclusion: Some months are not parts of the year
valid_syllogism :- month(X), \+ part_of_year(X).