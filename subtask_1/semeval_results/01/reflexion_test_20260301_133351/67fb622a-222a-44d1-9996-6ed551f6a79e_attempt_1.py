% Facts for a triangle that is a polygon and a geometric shape with three sides
triangle(tri1).
polygon(tri1).
geometric_shape_with_three_sides(tri1).

% Facts for a geometric shape with three sides that is NOT a polygon (counterexample)
geometric_shape_with_three_sides(shape2).

% Rule from first premise: All triangles are polygons
polygon(X) :- triangle(X).

% Rule from second premise: All triangles are geometric shapes with three sides
geometric_shape_with_three_sides(X) :- triangle(X).

% Validity check: Some geometric shapes with three sides are not polygons
valid_syllogism :- geometric_shape_with_three_sides(X), \+ polygon(X).