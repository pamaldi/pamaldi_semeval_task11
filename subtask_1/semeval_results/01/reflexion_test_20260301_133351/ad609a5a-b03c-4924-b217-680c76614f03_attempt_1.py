% Facts for writing_utensil and pencil
writing_utensil(pen1).
pencil(pencil1).

% Fail clauses for animal (no facts)
animal(_) :- fail.

% Rules from premises
animal(X) :- writing_utensil(X).  % All writing_utensil are animal
conflict :- pencil(X), animal(X). % No pencil is animal

% Validity check: Some writing_utensils are not pencils
valid_syllogism :- writing_utensil(X), \+ pencil(X).