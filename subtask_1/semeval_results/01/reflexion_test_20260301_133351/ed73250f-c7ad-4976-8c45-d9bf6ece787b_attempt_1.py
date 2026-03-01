% Witness: a yellow rose
rose(yellow_rose).

% A rose is a flower
flower(X) :- rose(X).

% Validity check: Some flowers are yellow
valid_syllogism :- flower(X), yellow(X).

% Define yellow for the witness
yellow(yellow_rose).