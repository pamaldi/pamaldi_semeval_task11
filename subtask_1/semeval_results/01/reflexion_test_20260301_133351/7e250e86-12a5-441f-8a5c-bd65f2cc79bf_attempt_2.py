% Facts for humans (we need at least one human that is a stone and not a living thing)
human(stone1).

% Rules from premises
stone(X) :- human(X).

% E-premise constraint: No living thing is a stone
conflict :- living_thing(X), stone(X).

% Validity check: Some human is not a living thing
valid_syllogism :- human(X), \+ living_thing(X).