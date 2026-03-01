% Facts for pencils
pencil(pencil1).

% stationery has no food items
% food has no stationery items
food(food1).

% P1: Every pencil is stationery
stationery(X) :- pencil(X).

% P2: No stationery is food
conflict :- stationery(X), food(X).

% C: Some food are not pencils
valid_syllogism :- food(X), \+ pencil(X).