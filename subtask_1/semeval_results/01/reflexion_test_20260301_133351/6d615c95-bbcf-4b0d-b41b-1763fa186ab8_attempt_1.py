% Witness: an apple that is also a fruit
apple(granny).
fruit(granny).

% mammal has NO facts in this model
mammal(_) :- fail.

% Rule from A-premise: All apples are fruits
fruit(X) :- apple(X).

% E-premise constraint: No apple is a mammal
conflict :- apple(X), mammal(X).

% Validity check: No fruit is a mammal
valid_syllogism :- \+ (fruit(X), mammal(X)).