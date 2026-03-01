% Fail clause for celestial_object (no facts, no rules)
celestial_object(_) :- fail.

% Rule from first premise: No organic_thing is a celestial_object
conflict :- organic_thing(X), celestial_object(X).

% Rule from second premise: Every planet is an organic_thing
organic_thing(X) :- planet(X).

% Validity check: No planet is a celestial_object
valid_syllogism :- \+ (planet(X), celestial_object(X)).