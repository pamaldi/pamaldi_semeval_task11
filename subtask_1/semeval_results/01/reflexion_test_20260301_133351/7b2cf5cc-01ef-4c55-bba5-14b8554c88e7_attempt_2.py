% Facts for predicates that have instances
triangle(t1).

% Predicates without instances (use fail clause)
square(_) :- fail.
rectangle(_) :- fail.

% Rule from the first premise: All squares are rectangles
rectangle(X) :- square(X).

% Validity check for the conclusion: Some triangles are not squares
valid_syllogism :- triangle(X), \+ square(X).