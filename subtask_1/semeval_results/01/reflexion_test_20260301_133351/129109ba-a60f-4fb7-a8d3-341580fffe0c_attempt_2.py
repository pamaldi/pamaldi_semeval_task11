% Facts for I-premise: Some rose is a plant
rose(rose1).
plant(rose1).

% Mammals has no facts (E-premise: No plant is a mammal)
mammal(_) :- fail.

% Rule from E-premise: No plant is a mammal
conflict :- plant(X), mammal(X).

% COUNTEREXAMPLE: roses can be mammals
% This will make the conclusion "No roses are mammals" FALSE
% We add a fact that makes a rose a mammal
mammal(rose1).

% E-conclusion check: "No roses are mammals" should be FALSE
valid_syllogism :- \+ (rose(X), mammal(X)).