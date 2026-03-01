% Witness: an apple that is a fruit
apple(a1).
fruit(a1).

% Rule from first premise: All fruit grow from plants
grows_from_plants(X) :- fruit(X).

% Validity check: Some apples grow from plants
valid_syllogism :- apple(X), grows_from_plants(X).