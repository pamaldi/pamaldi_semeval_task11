% Facts for daisies that are not insects
daisy(non_flower_insect).

% Rule from first premise: All flowers are insects
insect(X) :- flower(X).

% Validity check: Some daisies are not flowers
valid_syllogism :- daisy(X), \+ flower(X).