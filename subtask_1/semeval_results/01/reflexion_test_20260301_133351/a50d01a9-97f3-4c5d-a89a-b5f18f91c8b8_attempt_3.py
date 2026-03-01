% Facts for witness (square that is not a 4-sided shape)
square(w1).

% Fail clause for 4_sided_shape/1 since it has no facts
four_sided_shape(_) :- fail.

% Rules from premises
% "No circle is a 4-sided shape" → conflict if circle(X) and four_sided_shape(X)
conflict :- circle(X), four_sided_shape(X).

% "Every circle is a square" → square(X) if circle(X)
square(X) :- circle(X).

% Validity check for conclusion: Some squares are not 4-sided shapes
valid_syllogism :- square(X), \+ four_sided_shape(X).