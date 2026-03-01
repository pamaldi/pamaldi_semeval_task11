% This syllogism is invalid. We will construct a counterexample.

% All four-sided-shapes are both rectangles AND squares
four_sided_shape(s1).
rectangle(s1).
square(s1).

% Rule from first premise: All four_sided_shape are rectangle
rectangle(X) :- four_sided_shape(X).

% Rule from second premise: All four_sided_shape are square
square(X) :- four_sided_shape(X).

% Validity check: Some squares are not rectangles
valid_syllogism :- square(X), \+ rectangle(X).