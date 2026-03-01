% Witnesses
inanimate1(writer1).
inanimate2(people1).

% people has some facts
people(people1).
writer(writer1).

% Fail clause for inanimate since it has facts (inanimate1, inanimate2)
% No need for fail clause for writer or people

% Rules from premises
% No inanimate is a writer (E-proposition)
conflict :- inanimate(X), writer(X).

% A portion of inanimate objects are people (I-proposition)
people(X) :- inanimate(X), X = people1.

% Validity check: Some people are writers (I-conclusion)
valid_syllogism :- people(X), writer(X).