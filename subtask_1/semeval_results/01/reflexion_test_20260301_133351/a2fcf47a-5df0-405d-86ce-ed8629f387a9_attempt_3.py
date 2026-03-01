% Facts for fruits (witness)
fruit(apple).

% Facts for vegetables (witnesses) in our counterexample
vegetable(carrot).

% food rule from first premise (All fruits are food)
food(X) :- fruit(X).

% Second premise (No vegetable is a food)
% We must encode this constraint to ensure vegetables are not foods
conflict :- vegetable(X), food(X).

% Conclusion check: Every vegetable is a fruit
% We want this to FAIL in our counterexample
valid_syllogism :- \+ (vegetable(X), \+ fruit(X)).