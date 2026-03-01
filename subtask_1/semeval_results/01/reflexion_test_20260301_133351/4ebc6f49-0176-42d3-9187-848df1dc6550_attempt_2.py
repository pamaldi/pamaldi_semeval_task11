% COUNTEREXAMPLE: fruits and oranges are disjoint
% No overlap between fruits that are oranges and fruits that are apples

% Witness for fruits that are apples
fruit(apple1).
apple(apple1).

% Witness for fruits that are NOT oranges
fruit(banana1).

% E-premise constraint: No orange is an apple
conflict :- orange(X), apple(X).

% A-premise constraint: All apples are fruits
fruit(X) :- apple(X).

% I-premise: Some fruits are oranges → FALSE in our counterexample
% We have no fruits that are oranges

% Validity check for conclusion "Some fruits are oranges" (should FAIL)
valid_syllogism :- fruit(X), orange(X).