% Facts for berries that are fruits (I-proposition)
berry(blueberry).
fruit(blueberry).

% Fail clause for citrus berries (E-proposition)
conflict :- citrus(X), berry(X).

% Fail clause for citrus (no facts needed)
citrus(_) :- fail.

% Validity check: "Not all fruits are citrus" (O-proposition)
valid_syllogism :- fruit(X), \+ citrus(X).