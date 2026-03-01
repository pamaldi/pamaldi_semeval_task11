% Facts: no witnesses for metal or mammal
% Fail clauses for metal and mammal (completely empty)
metal(_) :- fail.
mammal(_) :- fail.

% Facts for snakes (we need to define instances of snakes)
snake(cobra).
snake(anaconda).

% Rule from second premise: All snakes are not metals
% We encode the constraint explicitly (though it's automatically true with empty metal/1)
conflict :- snake(X), metal(X).

% Validity check: No snake is a mammal
valid_syllogism :- \+ (snake(X), mammal(X)).