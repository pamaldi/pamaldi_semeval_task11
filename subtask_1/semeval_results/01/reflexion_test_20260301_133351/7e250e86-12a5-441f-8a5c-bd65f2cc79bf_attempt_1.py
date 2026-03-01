% Facts for living things (none, so no fail clause)
% Facts for stones (none, so no fail clause)
% Facts for humans (we need a human that is a stone, and not a living thing)
human(stone1).

% Rules from premises
stone(X) :- human(X).
conflict :- living_thing(X), stone(X).

% Validity check: Some human is not a living thing
valid_syllogism :- human(X), \+ living_thing(X).