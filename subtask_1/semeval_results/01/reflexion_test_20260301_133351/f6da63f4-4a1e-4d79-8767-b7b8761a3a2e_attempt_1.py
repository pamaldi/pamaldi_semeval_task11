% Witness: a snake that is a reptile but does NOT have fur
snake(cobra).
reptile(cobra).

% Rule from premise: No reptiles have fur
fur(_) :- fail.

% Rule from premise: All snakes are reptiles
reptile(X) :- snake(X).

% Validity check: Some snakes have fur
valid_syllogism :- snake(X), fur(X).