% Facts: no witnesses for metal or mammal
% Fail clauses for metal and mammal (completely empty)
metal(_) :- fail.
mammal(_) :- fail.

% Rule from second premise: All snakes are not metals
% (metal is empty, so this is automatically true)
% But we encode the constraint explicitly
conflict :- snake(X), metal(X).

% Validity check: No snake is a mammal
valid_syllogism :- \+ (snake(X), mammal(X)).