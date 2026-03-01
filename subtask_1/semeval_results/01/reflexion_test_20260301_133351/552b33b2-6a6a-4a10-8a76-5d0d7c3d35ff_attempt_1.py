% E-premise: No bird is a triangle
conflict :- bird(X), triangle(X).

% A-premise: Every triangle is a shape
shape(X) :- triangle(X).

% Fail clause for triangle (since no triangle is a bird, and we need to check for counterexample)
triangle(_) :- fail.

% Fail clause for bird (since no bird is a triangle, and we need to check for counterexample)
bird(_) :- fail.

% Fail clause for shape (since we want to test if some shapes are birds, so start with empty)
shape(_) :- fail.

% Validity check: Some shapes are birds → must find a shape that is a bird
valid_syllogism :- shape(X), bird(X).