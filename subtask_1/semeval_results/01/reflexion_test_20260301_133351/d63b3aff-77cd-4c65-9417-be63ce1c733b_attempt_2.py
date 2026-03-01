% COUNTEREXAMPLE: All apples are vegetables (making the conclusion false)
apple(a1).

% Rule: All apples are fruits (premise 2)
fruit(X) :- apple(X).

% Rule: All fruits are edible (premise 1)
edible(X) :- fruit(X).

% Counterexample: All apples are vegetables (this makes the conclusion false)
vegetable(X) :- apple(X).

% Validity check: Some apples are NOT vegetables (should FAIL)
valid_syllogism :- apple(X), \+ vegetable(X).