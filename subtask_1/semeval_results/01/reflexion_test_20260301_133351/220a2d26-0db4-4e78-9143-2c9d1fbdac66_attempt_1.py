% Witness for tennis player and athlete
tennis_player(maria).
athlete(maria).

% Rule from first premise: All athletes can photosynthesize
photosynthesize(X) :- athlete(X).

% Validity check: At least one tennis player can photosynthesize
valid_syllogism :- tennis_player(X), photosynthesize(X).