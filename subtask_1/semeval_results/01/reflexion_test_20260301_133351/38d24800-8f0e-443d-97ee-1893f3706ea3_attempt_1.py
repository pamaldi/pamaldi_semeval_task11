% Witness: a vertebrate that is NOT a creature
vertebrate(whale).

% fish has NO facts, so we need fail clause
fish(_) :- fail.

% Rule from first premise: No fish is a creature
conflict :- fish(X), creature(X).

% Rule from second premise: All fish are vertebrates
vertebrate(X) :- fish(X).

% Validity check: Some vertebrates are not creatures
valid_syllogism :- vertebrate(X), \+ creature(X).