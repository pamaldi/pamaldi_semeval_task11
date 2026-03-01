% Facts
part_of_year(january).
part_of_year(february).
month(january).
month(february).

% A-premise: All parts of the year are days
day(X) :- part_of_year(X).

% E-premise: No months are days
conflict :- month(X), day(X).

% Counterexample: All months are parts of the year (making the conclusion false)
% These facts satisfy the premises but contradict the conclusion

% O-conclusion: Some months are not parts of the year
% This should fail to show the syllogism is invalid
valid_syllogism :- month(X), \+ part_of_year(X).