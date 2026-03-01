% Witness for fruits that are also oranges
fruit(orange1).
orange(orange1).

% Fail clause for apples since they have no facts
apple(_) :- fail.

% E-premise constraint: No orange is an apple
conflict :- orange(X), apple(X).

% A-premise constraint: All apples are fruits
fruit(X) :- apple(X).

% I-conclusion: Some fruits are oranges
valid_syllogism :- fruit(X), orange(X).