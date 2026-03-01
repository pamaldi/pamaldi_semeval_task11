% Witness: a robot that is also a dolphin
robot(robodolphin).
dolphin(robodolphin).

% All dolphins are fish
fish(X) :- dolphin(X).

% Validity check: Some fish are robots
valid_syllogism :- fish(X), robot(X).