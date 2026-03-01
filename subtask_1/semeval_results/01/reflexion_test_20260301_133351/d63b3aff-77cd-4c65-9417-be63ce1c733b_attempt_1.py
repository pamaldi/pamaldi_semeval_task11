% Witness: an apple (which is a fruit)
apple(a1).

% Rule: Any apple is a fruit
fruit(X) :- apple(X).

% Rule: Every piece of fruit is edible
edible(X) :- fruit(X).

% vegetables has no facts, so the conclusion "some apples are not vegetables" 
% is interpreted as "some apples are not vegetables" → we test for apple(X), \+ vegetable(X)

% vegetables is empty in this model
vegetable(_) :- fail.

% Validity check: Some apples are not vegetables
valid_syllogism :- apple(X), \+ vegetable(X).