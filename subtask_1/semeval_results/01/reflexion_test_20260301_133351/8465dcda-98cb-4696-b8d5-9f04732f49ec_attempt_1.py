% No facts for 'idea'
idea(_) :- fail.

% Facts for 'liquid'
liquid(water).

% Rule from premise: Everything that is a liquid is a number
number(X) :- liquid(X).

% Rule from premise: No number is an idea
conflict :- number(X), idea(X).

% Validity check: every liquid is an idea
valid_syllogism :- \+ (liquid(X), \+ idea(X)).