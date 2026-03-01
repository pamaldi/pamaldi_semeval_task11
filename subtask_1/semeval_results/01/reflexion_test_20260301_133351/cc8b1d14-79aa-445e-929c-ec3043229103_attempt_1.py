% Facts for buses (some vehicles are buses)
vehicle(b1).
vehicle(b2).
vehicle(b3).

bus(b1).
bus(b2).

% vehicle is not a type of transportation (E-premise)
% So transportation has no facts, and we add a fail clause
transportation(_) :- fail.

% Validity check for conclusion "Some buses are not transportation"
valid_syllogism :- bus(X), \+ transportation(X).