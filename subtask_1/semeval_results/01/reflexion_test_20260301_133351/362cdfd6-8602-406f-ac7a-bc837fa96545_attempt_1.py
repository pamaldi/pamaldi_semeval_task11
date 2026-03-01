% Facts for plants and flowers
plant(wildflower).
flower(wildflower).

% Fail clause for animals since there are no animals that are plants
animal(_) :- fail.

% E-premise constraint: No plants are animals
conflict :- plant(X), animal(X).

% I-premise: Some flower is a plant (already satisfied by wildflower)

% E-conclusion: No flowers are animals
valid_syllogism :- \+ (flower(X), animal(X)).