% Facts for inanimate objects that are people (I-proposition witness)
inanimate(writer1).
inanimate(people1).

% people and writer facts
people(people1).
writer(writer1).

% Rule from E-premise: No inanimate is a writer
conflict :- inanimate(X), writer(X).

% Rule from I-premise: Some inanimate objects are people
people(X) :- inanimate(X), X = people1.

% Validity check: Some people are writers (I-conclusion)
valid_syllogism :- people(X), writer(X).