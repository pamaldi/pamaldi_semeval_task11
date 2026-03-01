% COUNTEREXAMPLE: A flower that IS an animal (contradicting the conclusion)

% I-premise: Some flower is a plant
flower(red_flower).
plant(red_flower).

% Counterexample: This flower is also an animal (making conclusion false)
animal(red_flower).

% E-premise constraint: No plant is an animal
% But this is violated in our counterexample
conflict :- plant(X), animal(X).

% E-conclusion: No flowers are animals
% This should FAIL in our counterexample
valid_syllogism :- \+ (flower(X), animal(X)).