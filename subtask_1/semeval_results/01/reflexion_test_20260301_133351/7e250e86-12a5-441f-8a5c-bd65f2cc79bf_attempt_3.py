% Facts for humans (we need at least one human that is a stone and not a living thing)
human(stone1).

% Rules from premises
stone(X) :- human(X).

% Validity check: Some human is not a living thing
valid_syllogism :- human(X), \+ living_thing(X).