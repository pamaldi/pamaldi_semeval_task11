% Facts (only needed for entities if we had a specific I/O type conclusion)
% None needed here since we are only making general statements

% Fail clause for circle (no circles exist in this model)
circle(_) :- fail.

% Rules from premises
quadrilateral(X) :- square(X).

% E-premise constraint: No quadrilateral is a circle
conflict :- quadrilateral(X), circle(X).

% E-conclusion: No circle is a square
valid_syllogism :- \+ (circle(X), square(X)).