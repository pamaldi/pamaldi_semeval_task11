% Witness for triangles and squares (counterexample entities)
triangle(t1).

% All triangles are squares - this makes the conclusion ("some triangles are not squares") false
square(t1).

% polygon_with_seven_sides has no facts
polygon_with_seven_sides(_) :- fail.

% E-premise: No polygon with seven sides is a square
conflict :- polygon_with_seven_sides(X), square(X).

% E-premise: No triangle is a polygon with seven sides
conflict2 :- triangle(X), polygon_with_seven_sides(X).

% O-conclusion: Some triangles are not squares
valid_syllogism :- triangle(X), \+ square(X).