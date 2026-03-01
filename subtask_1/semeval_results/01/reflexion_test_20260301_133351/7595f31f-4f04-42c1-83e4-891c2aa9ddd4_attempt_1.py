% Witness: a vegetable that is not green (counterexample to "All vegetables are green")
vegetable(carrot).
green(carrot) :- fail.

% All vegetables are plants
plant(X) :- vegetable(X).

% Validity check: Some plants are green
valid_syllogism :- plant(X), green(X).