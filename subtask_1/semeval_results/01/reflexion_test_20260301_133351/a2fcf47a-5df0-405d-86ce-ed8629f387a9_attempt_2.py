% Facts for fruits (witness)
fruit(apple).

% food rule from first premise (All fruits are food)
food(X) :- fruit(X).

% vegetable is not a food (Second premise)
% We do not have any vegetable facts, so food(X) will fail for vegetables
% Therefore, no need for a fail clause for food(X) if vegetable(X), because food/1 is already defined

% Conclusion to check: Every vegetable is a fruit
% We will construct a counterexample: a vegetable that is not a fruit
% Since we have no vegetable facts, we define a vegetable
vegetable(carrot).

% vegetable is not a fruit in our counterexample
% Conclusion check: is there a vegetable that is not a fruit?
valid_syllogism :- vegetable(X), \+ fruit(X).