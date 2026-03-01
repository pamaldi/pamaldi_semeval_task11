% Witness: a sweet food that is a berry
sweet_food(strawberry).
berry(strawberry).

% All berries are fruits
fruit(X) :- berry(X).

% Validity check: Some fruits are sweet foods
valid_syllogism :- fruit(X), sweet_food(X).