% Witnesses: an apple that is also a fruit
apple(a1).
fruit(a1).

% A-premise: All apples are delicious foods
delicious_food(X) :- apple(X).

% I-premise: Some apples are fruits (already encoded in facts)

% Validity check for conclusion: Some fruits are delicious foods
valid_syllogism :- fruit(X), delicious_food(X).