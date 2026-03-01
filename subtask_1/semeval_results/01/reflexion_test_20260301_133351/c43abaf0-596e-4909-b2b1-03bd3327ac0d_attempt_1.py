% Witness: a shark that is a fish and has legs
shark(hammerhead).
fish(hammerhead).
has_legs(hammerhead).

% No sharks that are not fish
conflict :- shark(X), \+ fish(X).

% Everything that is a fish has legs
has_legs(X) :- fish(X).

% Conclusion check: Some sharks have legs
valid_syllogism :- shark(X), has_legs(X).