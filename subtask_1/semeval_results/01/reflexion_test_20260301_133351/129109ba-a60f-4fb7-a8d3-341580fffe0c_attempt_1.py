% Witness: a rose that is a plant
plant(rose1).
rose(rose1).

% mammals has no facts
mammal(_) :- fail.

% E-premise constraint: No plant is a mammal
conflict :- plant(X), mammal(X).

% I-premise: Some plant is a rose (since rose(rose1) and plant(rose1))
% E-conclusion: No rose is a mammal
valid_syllogism :- \+ (rose(X), mammal(X)).