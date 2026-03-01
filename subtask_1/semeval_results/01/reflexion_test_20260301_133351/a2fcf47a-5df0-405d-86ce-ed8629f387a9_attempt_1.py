% Facts for fruits (witness)
fruit(apple).

% food rule from first premise (All fruits are food)
food(X) :- fruit(X).

% vegetable is not a food (Second premise)
% We do not have any vegetable facts, so food(X) will fail for vegetables
% Therefore, no need for a fail clause for food(X) if vegetable(X), because food/1 is already defined

% Conclusion to check: Every vegetable is a fruit
% We must show that for every vegetable, it is a fruit

% We will construct a counterexample: a vegetable that is not a fruit
valid_syllogism :- vegetable(carrot), \+ fruit(carrot).