% Witness: a triangle that is NOT a rectangle
triangle(t1).

% rectangle has NO facts in this model
rectangle(_) :- fail.

% Rule from first premise
rectangle(X) :- square(X).

% Validity check for conclusion: Some triangle is not a square
valid_syllogism :- triangle(X), \+ square(X).