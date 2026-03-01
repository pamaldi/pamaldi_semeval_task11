% Facts for counterexample (comet exists but is NOT a celestial body)
comet(halley).

% Fail clause for predicates with no facts (celestial_body has none)
celestial_body(_) :- fail.

% Rule from premise 1: All planets are celestial bodies
celestial_body(X) :- planet(X).

% Rule from premise 3: All comets are planets
planet(X) :- comet(X).

% Validity check - this should FAIL to show the syllogism is INVALID
valid_syllogism :- \+ (comet(X), celestial_body(X)).