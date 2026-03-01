% COUNTEREXAMPLE: Some snakes ARE mammals (contrary to the conclusion)
snake(human_snake).   % This snake is actually a mammal!
mammal(human_snake).

% Facts for metals (empty to satisfy "no metal is mammal")
metal(_) :- fail.

% Rules from first premise: No metal is a mammal
conflict :- metal(X), mammal(X).

% Rules from second premise: No snake is a metal
% Since metal/1 is completely empty, this is already true

% Validity check: The conclusion claims "No snakes are mammals"
% In our counterexample, this is FALSE (human_snake is both snake and mammal)
valid_syllogism :- \+ (snake(X), mammal(X)).