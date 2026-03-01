% Facts: No lakes are flowing bodies of water, so we don't assert any lake as flowing
% To ensure no lake is a flowing body, assert lake(_) fails
lake(_) :- fail.

% Every river is a flowing body of water
flowing_body_of_water(X) :- river(X).

% River example
river(nile).

% Validity check: No river is a lake
valid_syllogism :- \+ (river(X), lake(X)).