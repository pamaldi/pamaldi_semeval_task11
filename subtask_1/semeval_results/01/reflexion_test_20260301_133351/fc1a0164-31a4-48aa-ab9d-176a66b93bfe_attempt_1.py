% Facts
square(s1).

% Fail clauses for predicates with no facts
circle(_) :- fail.
quadrilateral(_) :- fail.

% Rules from premises
quadrilateral(X) :- square(X).
conflict :- circle(X), square(X).

% Validity check
valid_syllogism :- \+ (circle(X), quadrilateral(X)).