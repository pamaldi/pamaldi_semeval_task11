% Witness: a sun that is a star
sun(sol).
star(sol).

% celestial_body has no facts (E-premise)
celestial_body(_) :- fail.

% Rule from A-premise
star(X) :- sun(X).

% Validity check: Some sun is not a celestial body
valid_syllogism :- sun(X), \+ celestial_body(X).