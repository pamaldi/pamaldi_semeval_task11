% Counterexample: circle and square are different entities
circle(circle1).
square(square1).

% Rules from A-premises
shape(X) :- square(X).
shape(X) :- circle(X).

% A-conclusion: Every circle is a square
valid_syllogism :- \+ (circle(X), \+ square(X)).