% COUNTEREXAMPLE: Build a world where premises are true but conclusion is false

% Witness facts for premises
circle(c1).       % A circle exists
square(s1).       % A square exists
quadrilateral(s1). % The square is a quadrilateral
quadrilateral(c1). % The circle is a quadrilateral (this makes the conclusion false)

% Rules from premises
quadrilateral(X) :- square(X).  % All squares are quadrilaterals
conflict :- circle(X), square(X).  % No circle is a square

% Validity check (conclusion is "No circle is a quadrilateral")
valid_syllogism :- \+ (circle(X), quadrilateral(X)).  % Should FAIL