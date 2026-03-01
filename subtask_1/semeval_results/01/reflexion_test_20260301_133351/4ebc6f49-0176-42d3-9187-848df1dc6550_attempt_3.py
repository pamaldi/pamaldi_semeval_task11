% Facts for witnesses
% Witness for apple that is a fruit
apple(apple1).
fruit(apple1).

% Witness for fruit that is NOT an apple
fruit(banana1).

% Fail clauses for predicates with no facts (orange, conflict)
orange(_) :- fail.
conflict :- fail.

% A-premise: All apples are fruits
fruit(X) :- apple(X).

% E-premise: No orange is an apple
conflict :- orange(X), apple(X).

% I-conclusion: Some fruits are oranges (should fail in this counterexample)
valid_syllogism :- fruit(X), orange(X).