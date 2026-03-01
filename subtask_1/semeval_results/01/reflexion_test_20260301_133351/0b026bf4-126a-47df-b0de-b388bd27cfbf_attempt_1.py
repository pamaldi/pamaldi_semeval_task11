% Witness: a fruit that is NOT an apple
fruit(grape).
\+ apple(grape).

% All fruits are foods
food(X) :- fruit(X).

% Apple has no facts, so use fail clause
apple(_) :- fail.

% Validity check: some food is not an apple
valid_syllogism :- food(X), \+ apple(X).