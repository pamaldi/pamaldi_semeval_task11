% Witness: a whale that is a mammal
whale(blue).
mammal(blue).

% No fish is a mammal
fish(_) :- fail.
mammal(X) :- fail, fish(X).  % Prevent overlap between fish and mammals

% Validity check: Some whales are not fish
valid_syllogism :- whale(X), \+ fish(X).