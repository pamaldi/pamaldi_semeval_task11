% Facts for daisies that are not insects
daisy(breaking_the_premise).

% Rule from first premise: All flowers are insects
insect(X) :- flower(X).

% Fail clause for flowers since we have no facts about flowers
flower(_) :- fail.

% Validity check: Some daisies are not flowers
valid_syllogism :- daisy(X), \+ flower(X).