% Witness for wolves that are not cows
wolf(alpha).

% cow has NO facts in this model
cow(_) :- fail.

% Rule from first premise: All cows are farm animals
farm_animal(X) :- cow(X).

% Rule from second premise: No wolves are farm animals
conflict :- wolf(X), farm_animal(X).

% Third premise: Some wolves are not cows
% Already true since cow(_) fails

% Validity check: Some wolves are not cows
valid_syllogism :- wolf(X), \+ cow(X).