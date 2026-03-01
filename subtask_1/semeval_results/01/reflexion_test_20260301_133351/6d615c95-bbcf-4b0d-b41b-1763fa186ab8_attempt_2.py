% Counterexample: apple is a fruit, but NOT the only fruit
% We need: 
% 1. No apples are mammals (true)
% 2. All apples are fruits (true)
% 3. But: Some fruits ARE mammals (makes conclusion false)

% Witness apple
apple(granny).
fruit(granny).

% Counterexample: Another fruit that IS a mammal
fruit(mammal_fruit).
mammal(mammal_fruit).

% E-premise: No apple is a mammal
% This is already true because apple(granny) exists but no mammal(granny)

% A-premise: All apples are fruits
fruit(X) :- apple(X).

% Validity check: No fruit is a mammal (this should fail)
valid_syllogism :- \+ (fruit(X), mammal(X)).